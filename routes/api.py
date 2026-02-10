"""API routes"""
from flask import Blueprint, request, jsonify, session
from routes.chat import login_required


def create_api_blueprint(get_db_service):
    """Create API blueprint"""
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    
    @api_bp.route('/user')
    def get_user():
        if 'user_id' in session:
            db_service = get_db_service()
            user = db_service.get_user_by_id(session['user_id'])
            if user:
                return jsonify({
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'picture': user.picture_url or '',
                    'auth_type': user.auth_type
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
        db_service = get_db_service()
        status = db_service.get_api_keys_status(user_id)
        return jsonify(status)
    
    @api_bp.route('/keys', methods=['POST'])
    @login_required
    def save_keys():
        data = request.json
        user_id = session['user_id']
        db_service = get_db_service()
        
        for provider in ['openai', 'anthropic', 'google']:
            key = data.get(provider, '').strip()
            if key:
                db_service.save_api_key(user_id, provider, key)
        
        return jsonify({"success": True})
    
    @api_bp.route('/conversations', methods=['GET'])
    @login_required
    def get_conversations():
        user_id = session['user_id']
        db_service = get_db_service()
        conversations = db_service.get_user_conversations(user_id)
        
        result = [
            {
                "id": conv.id,
                "title": conv.title,
                "timestamp": conv.updated_at.isoformat(),
                "provider": conv.provider,
                "model": conv.model,
                "total_messages": conv.total_messages,
                "total_cost": float(conv.total_cost)
            }
            for conv in conversations
        ]
        return jsonify(result)
    
    @api_bp.route('/conversations', methods=['POST'])
    @login_required
    def create_conversation():
        user_id = session['user_id']
        db_service = get_db_service()
        
        data = request.json
        conv = db_service.create_conversation(
            user_id,
            "New Chat",
            data.get("provider", "openai"),
            data.get("model", "gpt-4o")
        )
        
        return jsonify({"id": conv.id})
    
    @api_bp.route('/conversations/<conv_id>', methods=['GET'])
    @login_required
    def get_conversation(conv_id):
        user_id = session['user_id']
        db_service = get_db_service()
        
        conv = db_service.get_conversation(conv_id)
        if not conv or conv.user_id != user_id:
            return jsonify({"error": "Conversation not found"}), 404
        
        messages = db_service.get_conversation_messages(conv_id)
        
        return jsonify({
            "id": conv.id,
            "title": conv.title,
            "provider": conv.provider,
            "model": conv.model,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "provider": msg.provider,
                    "model": msg.model,
                    "input_tokens": msg.input_tokens,
                    "output_tokens": msg.output_tokens,
                    "total_tokens": msg.total_tokens,
                    "cost": float(msg.cost),
                    "is_error": msg.is_error
                }
                for msg in messages
            ]
        })
    
    @api_bp.route('/conversations/<conv_id>', methods=['DELETE'])
    @login_required
    def delete_conversation(conv_id):
        user_id = session['user_id']
        db_service = get_db_service()
        
        conv = db_service.get_conversation(conv_id)
        if not conv or conv.user_id != user_id:
            return jsonify({"error": "Conversation not found"}), 404
        
        db_service.delete_conversation(conv_id)
        return jsonify({"success": True})
    
    return api_bp
