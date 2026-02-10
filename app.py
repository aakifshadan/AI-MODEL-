"""AI Chat Hub - Main Application"""
from flask import Flask
from authlib.integrations.flask_client import OAuth
from sqlalchemy.orm import scoped_session

from config import Config
from services import AIService
from services.database_service import DatabaseService
from models.database import get_engine, get_session_maker
from routes import register_routes
from routes.auth import setup_oauth


def create_app():
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize database
    engine = get_engine(app.config['DATABASE_URL'])
    SessionLocal = scoped_session(get_session_maker(engine))
    
    # Initialize services
    def get_db_service():
        session = SessionLocal()
        return DatabaseService(session, app.config['SECRET_KEY'])
    
    ai_service = AIService()
    
    # Setup OAuth
    oauth = OAuth(app)
    setup_oauth(app, oauth)
    
    # Register routes
    register_routes(app, get_db_service, ai_service)
    
    # Cleanup database sessions
    @app.teardown_appcontext
    def cleanup_db(error):
        SessionLocal.remove()
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        debug=app.config['DEBUG'],
        host=app.config['HOST'],
        port=app.config['PORT']
    )
