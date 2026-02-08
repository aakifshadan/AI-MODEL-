"""Authentication routes"""
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth


def create_auth_blueprint(user_service):
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
        
        users = user_service.load_users()
        
        # Check if email exists
        for user in users.values():
            if user.get('email') == email:
                return jsonify({'error': 'Email already registered'}), 400
        
        # Create new user
        user_id = str(uuid.uuid4())
        users[user_id] = {
            'id': user_id,
            'email': email,
            'name': name or email.split('@')[0],
            'password_hash': generate_password_hash(password, method='pbkdf2:sha256'),
            'auth_type': 'email',
            'created_at': datetime.now().isoformat()
        }
        user_service.save_users(users)
        
        # Log them in
        session['user_id'] = user_id
        
        return jsonify({'success': True, 'user': {'id': user_id, 'email': email, 'name': users[user_id]['name']}})
    
    @auth_bp.route('/auth/login', methods=['POST'])
    def login():
        data = request.json
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        users = user_service.load_users()
        
        for user_id, user in users.items():
            if user.get('email') == email and user.get('auth_type') == 'email':
                if check_password_hash(user.get('password_hash', ''), password):
                    session['user_id'] = user_id
                    return jsonify({'success': True, 'user': {'id': user_id, 'email': email, 'name': user['name']}})
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
        redirect_uri = 'http://localhost:5000/auth/google/callback'
        print(f"\n=== GOOGLE OAUTH DEBUG ===")
        print(f"Redirect URI: {redirect_uri}")
        print(f"Client ID: {app.config['GOOGLE_CLIENT_ID']}")
        print(f"Request URL: {request.url}")
        print(f"Request Host: {request.host}")
        print(f"=========================\n")
        return google.authorize_redirect(redirect_uri)
    
    @app.route('/auth/google/callback')
    def google_callback():
        from services import UserService
        user_service = UserService(app.config['SECRET_KEY'])
        
        try:
            token = google.authorize_access_token()
            user_info = token.get('userinfo')
            
            if not user_info:
                return redirect(url_for('auth.login_page') + '?error=Failed to get user info')
            
            email = user_info.get('email')
            name = user_info.get('name', email.split('@')[0])
            picture = user_info.get('picture', '')
            
            users = user_service.load_users()
            
            # Find or create user
            user_id = None
            for uid, user in users.items():
                if user.get('email') == email:
                    user_id = uid
                    users[uid]['picture'] = picture
                    users[uid]['name'] = name
                    break
            
            if not user_id:
                user_id = str(uuid.uuid4())
                users[user_id] = {
                    'id': user_id,
                    'email': email,
                    'name': name,
                    'picture': picture,
                    'auth_type': 'google',
                    'created_at': datetime.now().isoformat()
                }
            
            user_service.save_users(users)
            session['user_id'] = user_id
            
            return redirect(url_for('chat.index'))
        except Exception as e:
            return redirect(url_for('auth.login_page') + f'?error={str(e)}')
