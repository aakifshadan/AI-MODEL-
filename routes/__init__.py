"""Route handlers"""
from flask import Blueprint

def register_routes(app, user_service, ai_service):
    """Register all route blueprints"""
    from .auth import create_auth_blueprint
    from .chat import create_chat_blueprint
    from .api import create_api_blueprint
    
    # Register blueprints
    app.register_blueprint(create_auth_blueprint(user_service))
    app.register_blueprint(create_chat_blueprint(user_service, ai_service))
    app.register_blueprint(create_api_blueprint(user_service))
