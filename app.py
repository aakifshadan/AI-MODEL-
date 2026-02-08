"""AI Chat Hub - Main Application"""
from flask import Flask
from authlib.integrations.flask_client import OAuth

from config import Config
from services import UserService, AIService
from routes import register_routes
from routes.auth import setup_oauth


def create_app():
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize services
    user_service = UserService(
        secret_key=app.config['SECRET_KEY'],
        users_file=app.config['USERS_FILE'],
        user_data_dir=app.config['USER_DATA_DIR']
    )
    ai_service = AIService()
    
    # Setup OAuth
    oauth = OAuth(app)
    setup_oauth(app, oauth)
    
    # Register routes
    register_routes(app, user_service, ai_service)
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        debug=app.config['DEBUG'],
        host=app.config['HOST'],
        port=app.config['PORT']
    )
