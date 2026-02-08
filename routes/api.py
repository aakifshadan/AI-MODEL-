"""API routes"""
from flask import Blueprint, request, jsonify, session
from routes.chat import login_required


def create_api_blueprint(user_service):
    """Create API blueprint"""
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    
    @api_bp.route('/user')
    def get_user():
        if 'user_id' in session:
            users = user_service.load_users()
            user = users.get(session['user_id'])
            if user:
                return jsonify({
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'picture': user.get('picture', ''),
                    'auth_type': user.get('auth_type', 'email')
                })
        return jsonify(None)
    
    @api_bp.route('/models', methods=['GET'])
    @login_required
    def get_models():
        from models import MODELS
        return jsonify(MODELS)
    
    @api_bp.route('/keys', methods=['GET'])
    @login_required
    def get_keys_status():
        user_id = session['user_id']
        status = {}
        for provider in ['openai', 'anthropic', 'google']:
            key = user_service.get_api_key(user_id, provider)
            status[provider] = {
                'configured': bool(key),
                'masked': f"{'*' * 20}...{key[-4:]}" if key and len(key) > 4 else ""
            }
        return jsonify(status)
    
    @api_bp.route('/keys', methods=['POST'])
    @login_required
    def save_keys():
        data = request.json
        user_id = session['user_id']
        
        keys_to_save = {}
        for provider in ['openai', 'anthropic', 'google']:
            key = data.get(provider, '').strip()
            if key:
                keys_to_save[provider] = key
        
        user_service.save_api_keys(user_id, keys_to_save)
        return jsonify({"success": True})
    
    @api_bp.route('/conversations', methods=['GET'])
    @login_required
    def get_conversations():
        user_id = session['user_id']
        user_data = user_service.load_user_data(user_id)
        convos = user_data.get('conversations', {})
        
        result = [
            {"id": k, "title": v["title"], "timestamp": v["timestamp"], "provider": v["provider"], "model": v["model"]}
            for k, v in convos.items()
        ]
        return jsonify(sorted(result, key=lambda x: x["timestamp"], reverse=True))
    
    @api_bp.route('/conversations', methods=['POST'])
    @login_required
    def create_conversation():
        import uuid
        from datetime import datetime
        
        user_id = session['user_id']
        user_data = user_service.load_user_data(user_id)
        
        data = request.json
        conv_id = str(uuid.uuid4())
        
        if 'conversations' not in user_data:
            user_data['conversations'] = {}
        
        user_data['conversations'][conv_id] = {
            "id": conv_id,
            "title": "New Chat",
            "messages": [],
            "provider": data.get("provider", "openai"),
            "model": data.get("model", "gpt-4o"),
            "timestamp": datetime.now().isoformat()
        }
        
        user_service.save_user_data(user_id, user_data)
        return jsonify({"id": conv_id})
    
    @api_bp.route('/conversations/<conv_id>', methods=['GET'])
    @login_required
    def get_conversation(conv_id):
        user_id = session['user_id']
        user_data = user_service.load_user_data(user_id)
        convos = user_data.get('conversations', {})
        
        if conv_id in convos:
            return jsonify(convos[conv_id])
        return jsonify({"error": "Conversation not found"}), 404
    
    @api_bp.route('/conversations/<conv_id>', methods=['DELETE'])
    @login_required
    def delete_conversation(conv_id):
        user_id = session['user_id']
        user_data = user_service.load_user_data(user_id)
        
        if conv_id in user_data.get('conversations', {}):
            del user_data['conversations'][conv_id]
            user_service.save_user_data(user_id, user_data)
            return jsonify({"success": True})
        return jsonify({"error": "Conversation not found"}), 404
    
    return api_bp
