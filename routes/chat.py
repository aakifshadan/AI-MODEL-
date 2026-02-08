"""Chat routes"""
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session
from functools import wraps
from models import MODELS, calculate_cost


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            from flask import redirect, url_for
            return redirect(url_for('auth.login_page'))
        return f(*args, **kwargs)
    return decorated_function


def create_chat_blueprint(user_service, ai_service):
    """Create chat blueprint"""
    chat_bp = Blueprint('chat', __name__)
    
    @chat_bp.route('/')
    @login_required
    def index():
        return render_template('index.html', models=MODELS)
    
    @chat_bp.route('/api/chat', methods=['POST'])
    @login_required
    def chat():
        user_id = session['user_id']
        user_data = user_service.load_user_data(user_id)
        
        data = request.json
        user_message = data.get("message")
        provider = data.get("provider", "openai")
        model = data.get("model", "gpt-4o")
        conv_id = data.get("conversation_id")
        
        # Get API key
        from flask import current_app
        fallback_keys = {
            'OPENAI_API_KEY': current_app.config['OPENAI_API_KEY'],
            'ANTHROPIC_API_KEY': current_app.config['ANTHROPIC_API_KEY'],
            'GEMINI_API_KEY': current_app.config['GEMINI_API_KEY']
        }
        api_key = user_service.get_api_key(user_id, provider, fallback_keys)
        
        if not api_key:
            return jsonify({"error": f"API key not configured for {MODELS[provider]['name']}. Please add your API key in Settings."}), 400
        
        if 'conversations' not in user_data:
            user_data['conversations'] = {}
        
        # Get or create conversation
        if conv_id and conv_id in user_data['conversations']:
            conv = user_data['conversations'][conv_id]
            conv["provider"] = provider
            conv["model"] = model
        else:
            conv_id = str(uuid.uuid4())
            user_data['conversations'][conv_id] = {
                "id": conv_id,
                "title": user_message[:50] + "..." if len(user_message) > 50 else user_message,
                "messages": [],
                "provider": provider,
                "model": model,
                "timestamp": datetime.now().isoformat()
            }
            conv = user_data['conversations'][conv_id]
        
        conv["messages"].append({"role": "user", "content": user_message})
        
        if len(conv["messages"]) == 1:
            conv["title"] = user_message[:50] + "..." if len(user_message) > 50 else user_message

        try:
            result = ai_service.generate_response(provider, model, conv["messages"], api_key)
            
            # Calculate cost
            cost = calculate_cost(provider, model, result["input_tokens"], result["output_tokens"])
            
            conv["messages"].append({
                "role": "assistant", 
                "content": result["content"],
                "provider": provider,
                "model": model,
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"],
                "total_tokens": result["total_tokens"],
                "cost": cost
            })
            conv["timestamp"] = datetime.now().isoformat()
            user_service.save_user_data(user_id, user_data)
            
            return jsonify({
                "response": result["content"],
                "conversation_id": conv_id,
                "provider": provider,
                "model": model,
                "usage": {
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "total_tokens": result["total_tokens"],
                    "cost": round(cost, 6)
                }
            })

        except Exception as e:
            error_message = f"Error: {str(e)}"
            conv["messages"].append({
                "role": "assistant",
                "content": error_message,
                "provider": provider,
                "model": model,
                "is_error": True
            })
            conv["timestamp"] = datetime.now().isoformat()
            user_service.save_user_data(user_id, user_data)
            
            return jsonify({
                "error": str(e),
                "conversation_id": conv_id,
                "provider": provider,
                "model": model
            }), 500
    
    return chat_bp
