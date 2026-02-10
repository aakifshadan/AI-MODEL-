"""Authentication routes"""
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth


def create_auth_blueprint(get_db_service):
    """Create authentication blueprint"""
    auth_bp = Blueprint('auth', __name__)
    
    @auth_bp.route('/login')
    def login_page():
        if 'user_id' in session:
            return redirect(url_for('chat.index'))
        return render_template('login.html')
    
    @auth_bp.route('/auth/register', methods=['POST'])
    def register():
        data = request.json
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        db_service = get_db_service()
        
        # Check if email exists
        existing_user = db_service.get_user_by_email(email)
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create new user
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        user = db_service.create_user(
            email=email,
            name=name or email.split('@')[0],
            password_hash=password_hash,
            auth_type='email'
        )
        
        # Log them in
        session['user_id'] = user.id
        
        return jsonify({
            'success': True, 
            'user': {
                'id': user.id, 
                'email': user.email, 
                'name': user.name
            }
        })
    
    @auth_bp.route('/auth/login', methods=['POST'])
    def login():
        data = request.json
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        db_service = get_db_service()
        user = db_service.get_user_by_email(email)
        
        if user and user.auth_type == 'email':
            if check_password_hash(user.password_hash, password):
                session['user_id'] = user.id
                db_service.update_user_login(user.id)
                return jsonify({
                    'success': True, 
                    'user': {
                        'id': user.id, 
                        'email': user.email, 
                        'name': user.name
                    }
                })
            else:
                return jsonify({'error': 'Invalid password'}), 401
        
        return jsonify({'error': 'User not found'}), 404
    
    @auth_bp.route('/auth/logout')
    def logout():
        session.clear()
        return redirect(url_for('auth.login_page'))
    
    return auth_bp


def setup_oauth(app, oauth):
    """Setup OAuth for Google login"""
    google = oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
    
    @app.route('/auth/google')
    def google_login():
        # Check if credentials are configured
        if not app.config.get('GOOGLE_CLIENT_ID') or not app.config.get('GOOGLE_CLIENT_SECRET'):
            return redirect(url_for('auth.login_page') + '?error=Google OAuth not configured. Please add credentials to .env file')
        
        redirect_uri = 'http://localhost:5000/auth/google/callback'
        print(f"\n=== GOOGLE OAUTH DEBUG ===")
        print(f"Redirect URI: {redirect_uri}")
        print(f"Client ID: {app.config['GOOGLE_CLIENT_ID']}")
        print(f"Request URL: {request.url}")
        print(f"Request Host: {request.host}")
        print(f"=========================\n")
        
        try:
            return google.authorize_redirect(redirect_uri)
        except Exception as e:
            print(f"OAuth Error: {str(e)}")
            return redirect(url_for('auth.login_page') + f'?error=OAuth error: {str(e)}')
    
    @app.route('/auth/google/callback')
    def google_callback():
        from services.database_service import DatabaseService
        from models.database import get_engine, get_session_maker
        from sqlalchemy.orm import scoped_session
        
        # Initialize database service
        engine = get_engine(app.config['DATABASE_URL'])
        SessionLocal = scoped_session(get_session_maker(engine))
        session_db = SessionLocal()
        db_service = DatabaseService(session_db, app.config['SECRET_KEY'])
        
        try:
            token = google.authorize_access_token()
            user_info = token.get('userinfo')
            
            if not user_info:
                return redirect(url_for('auth.login_page') + '?error=Failed to get user info')
            
            email = user_info.get('email')
            name = user_info.get('name', email.split('@')[0])
            picture = user_info.get('picture', '')
            
            # Find or create user
            user = db_service.get_user_by_email(email)
            
            if user:
                # Update existing user
                db_service.update_user(user.id, 
                    name=name, 
                    picture_url=picture
                )
            else:
                # Create new user
                user = db_service.create_user(
                    email=email,
                    name=name,
                    picture_url=picture,
                    auth_type='google'
                )
            
            db_service.update_user_login(user.id)
            session['user_id'] = user.id
            
            return redirect(url_for('chat.index'))
        except Exception as e:
            print(f"OAuth callback error: {str(e)}")
            return redirect(url_for('auth.login_page') + f'?error={str(e)}')
        finally:
            session_db.close()
