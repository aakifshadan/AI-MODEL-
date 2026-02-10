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


def create_chat_blueprint(get_db_service, ai_service):
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
        db_service = get_db_service()
        
        data = request.json
        user_message = data.get("message")
        provider = data.get("provider", "openai")
        model = data.get("model", "gpt-4o")
        conv_id = data.get("conversation_id")
        stream = data.get("stream", True)  # Enable streaming by default
        
        # Get API key
        from flask import current_app
        fallback_keys = {
            'OPENAI_API_KEY': current_app.config['OPENAI_API_KEY'],
            'ANTHROPIC_API_KEY': current_app.config['ANTHROPIC_API_KEY'],
            'GEMINI_API_KEY': current_app.config['GEMINI_API_KEY']
        }
        api_key = db_service.get_api_key(user_id, provider)
        if not api_key:
            # Try fallback keys
            api_key = fallback_keys.get(f'{provider.upper()}_API_KEY', '')
        
        if not api_key:
            return jsonify({"error": f"API key not configured for {MODELS[provider]['name']}. Please add your API key in Settings."}), 400
        
        # Get or create conversation
        if conv_id:
            conv = db_service.get_conversation(conv_id)
            if not conv or conv.user_id != user_id:
                return jsonify({"error": "Conversation not found"}), 404
            # Update provider/model if changed
            if conv.provider != provider or conv.model != model:
                db_service.update_conversation(conv_id, provider=provider, model=model)
        else:
            # Create new conversation
            title = user_message[:50] + "..." if len(user_message) > 50 else user_message
            conv = db_service.create_conversation(user_id, title, provider, model)
            conv_id = conv.id
        
        # Add user message
        db_service.create_message(conv_id, "user", user_message)
        
        # Get conversation messages for context
        messages = db_service.get_conversation_messages(conv_id)
        message_list = [
            {"role": msg.role, "content": msg.content} 
            for msg in messages
        ]
        
        # Use streaming if requested
        if stream:
            return chat_stream_response(conv_id, provider, model, message_list, api_key, db_service, user_id)
        
        # Non-streaming response (legacy)
        try:
            result = ai_service.generate_response(provider, model, message_list, api_key)
            
            # Calculate cost
            cost = calculate_cost(provider, model, result["input_tokens"], result["output_tokens"])
            
            # Add assistant message
            db_service.create_message(
                conv_id, "assistant", result["content"],
                provider=provider, model=model,
                input_tokens=result["input_tokens"],
                output_tokens=result["output_tokens"],
                total_tokens=result["total_tokens"],
                cost=cost
            )
            
            # Update API key usage
            db_service.update_api_key_usage(user_id, provider)
            
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
            
            # Add error message
            db_service.create_message(
                conv_id, "assistant", error_message,
                provider=provider, model=model,
                is_error=True, error_message=str(e)
            )
            
            return jsonify({
                "error": str(e),
                "conversation_id": conv_id,
                "provider": provider,
                "model": model
            }), 500
    
    def chat_stream_response(conv_id, provider, model, message_list, api_key, db_service, user_id):
        """Handle streaming chat response"""
        import json
        from flask import Response
        
        def generate():
            full_response = ""
            try:
                # Send initial metadata
                yield f"data: {json.dumps({'type': 'start', 'conversation_id': conv_id})}\n\n"
                
                # Stream the response
                for chunk in ai_service.generate_response_stream(provider, model, message_list, api_key):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                
                # Estimate tokens (rough approximation)
                input_tokens = sum(len(m["content"].split()) for m in message_list)
                output_tokens = len(full_response.split())
                total_tokens = input_tokens + output_tokens
                cost = calculate_cost(provider, model, input_tokens, output_tokens)
                
                # Save the complete message to database
                db_service.create_message(
                    conv_id, "assistant", full_response,
                    provider=provider, model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost=cost
                )
                
                # Update API key usage
                db_service.update_api_key_usage(user_id, provider)
                
                # Send completion metadata
                yield f"data: {json.dumps({'type': 'done', 'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens, 'total_tokens': total_tokens, 'cost': round(cost, 6)}})}\n\n"
                
            except Exception as e:
                error_message = f"Error: {str(e)}"
                db_service.create_message(
                    conv_id, "assistant", error_message,
                    provider=provider, model=model,
                    is_error=True, error_message=str(e)
                )
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
    
    return chat_bp
