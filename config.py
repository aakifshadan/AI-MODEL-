"""Application configuration"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    # API Keys (fallback)
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    
    # Data storage
    USERS_FILE = 'users.json'
    USER_DATA_DIR = 'user_data'
    
    # Server
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000
