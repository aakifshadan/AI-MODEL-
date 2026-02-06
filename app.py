import os
import uuid
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from datetime import datetime
from cryptography.fernet import Fernet
import base64
import hashlib
from functools import wraps

# Auth imports
from authlib.integrations.flask_client import OAuth
from werkzeug.security import generate_password_hash, check_password_hash

# Import AI SDKs
import openai
import anthropic
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# OAuth Setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Encryption for API keys
def get_encryption_key():
    secret = app.secret_key if isinstance(app.secret_key, bytes) else app.secret_key.encode()
    key = hashlib.sha256(secret).digest()
    return base64.urlsafe_b64encode(key)

cipher = Fernet(get_encryption_key())

# Data storage files
USERS_FILE = 'users.json'
USER_DATA_DIR = 'user_data'

# Ensure user data directory exists
os.makedirs(USER_DATA_DIR, exist_ok=True)

# User management functions
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def get_user_data_path(user_id):
    return os.path.join(USER_DATA_DIR, f'{user_id}.json')

def load_user_data(user_id):
    path = get_user_data_path(user_id)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {'api_keys': {}, 'conversations': {}}

def save_user_data(user_id, data):
    path = get_user_data_path(user_id)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def get_current_user():
    """Get current logged in user info"""
    if 'user_id' in session:
        users = load_users()
        return users.get(session['user_id'])
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def get_api_key(provider):
    """Get API key for provider - from user data or env"""
    if 'user_id' in session:
        user_data = load_user_data(session['user_id'])
        encrypted_keys = user_data.get('api_keys', {})
        if encrypted_keys.get(provider):
            try:
                return cipher.decrypt(encrypted_keys[provider].encode()).decode()
            except:
                pass
    
    # Fall back to environment variables
    env_map = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY', 
        'google': 'GEMINI_API_KEY'
    }
    return os.getenv(env_map.get(provider, ''), '')


# Model configurations with pricing (per 1M tokens)
MODELS = {
    "openai": {
        "name": "OpenAI",
        "models": {
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini",
            "gpt-4-turbo": "GPT-4 Turbo",
            "gpt-3.5-turbo": "GPT-3.5 Turbo"
        },
        "pricing": {
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50}
        }
    },
    "anthropic": {
        "name": "Anthropic",
        "models": {
            "claude-sonnet-4-20250514": "Claude Sonnet 4",
            "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
            "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
            "claude-3-opus-20240229": "Claude 3 Opus"
        },
        "pricing": {
            "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
            "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
            "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
            "claude-3-opus-20240229": {"input": 15.00, "output": 75.00}
        }
    },
    "google": {
        "name": "Google",
        "models": {
            "gemini-2.5-flash": "Gemini 2.5 Flash",
            "gemini-2.5-pro": "Gemini 2.5 Pro",
            "gemini-2.0-flash": "Gemini 2.0 Flash",
            "gemini-1.5-pro": "Gemini 1.5 Pro"
        },
        "pricing": {
            "gemini-2.5-flash": {"input": 0.10, "output": 0.40},
            "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
            "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
            "gemini-1.5-pro": {"input": 1.25, "output": 5.00}
        }
    }
}

# ============ AUTH ROUTES ============

@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/auth/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    users = load_users()
    
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
    save_users(users)
    
    # Log them in
    session['user_id'] = user_id
    
    return jsonify({'success': True, 'user': {'id': user_id, 'email': email, 'name': users[user_id]['name']}})

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    
    users = load_users()
    
    for user_id, user in users.items():
        if user.get('email') == email and user.get('auth_type') == 'email':
            if check_password_hash(user.get('password_hash', ''), password):
                session['user_id'] = user_id
                return jsonify({'success': True, 'user': {'id': user_id, 'email': email, 'name': user['name']}})
            else:
                return jsonify({'error': 'Invalid password'}), 401
    
    return jsonify({'error': 'User not found'}), 404

@app.route('/auth/google')
def google_login():
    # Force localhost to avoid 127.0.0.1 vs localhost mismatch
    redirect_uri = 'http://localhost:5000/auth/google/callback'
    print(f"\n=== GOOGLE OAUTH DEBUG ===")
    print(f"Redirect URI: {redirect_uri}")
    print(f"Client ID: {os.environ.get('GOOGLE_CLIENT_ID')}")
    print(f"Request URL: {request.url}")
    print(f"Request Host: {request.host}")
    print(f"=========================\n")
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            return redirect(url_for('login_page') + '?error=Failed to get user info')
        
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        picture = user_info.get('picture', '')
        
        users = load_users()
        
        # Find or create user
        user_id = None
        for uid, user in users.items():
            if user.get('email') == email:
                user_id = uid
                # Update profile picture if changed
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
        
        save_users(users)
        session['user_id'] = user_id
        
        return redirect(url_for('index'))
    except Exception as e:
        return redirect(url_for('login_page') + f'?error={str(e)}')

@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/api/user')
def get_user():
    user = get_current_user()
    if user:
        return jsonify({
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'picture': user.get('picture', ''),
            'auth_type': user.get('auth_type', 'email')
        })
    return jsonify(None)


# ============ MAIN ROUTES ============

@app.route('/')
@login_required
def index():
    return render_template('index.html', models=MODELS)

@app.route('/api/models', methods=['GET'])
@login_required
def get_models():
    return jsonify(MODELS)

@app.route('/api/keys', methods=['GET'])
@login_required
def get_keys_status():
    status = {}
    for provider in ['openai', 'anthropic', 'google']:
        key = get_api_key(provider)
        status[provider] = {
            'configured': bool(key),
            'masked': f"{'*' * 20}...{key[-4:]}" if key and len(key) > 4 else ""
        }
    return jsonify(status)

@app.route('/api/keys', methods=['POST'])
@login_required
def save_keys():
    data = request.json
    user_id = session['user_id']
    user_data = load_user_data(user_id)
    
    existing_keys = user_data.get('api_keys', {})
    
    # Decrypt existing keys for merging
    decrypted_existing = {}
    for provider, encrypted in existing_keys.items():
        if encrypted:
            try:
                decrypted_existing[provider] = cipher.decrypt(encrypted.encode()).decode()
            except:
                decrypted_existing[provider] = ''
    
    # Merge with new keys
    for provider in ['openai', 'anthropic', 'google']:
        new_key = data.get(provider, '').strip()
        if new_key:
            decrypted_existing[provider] = new_key
    
    # Encrypt and save
    user_data['api_keys'] = {
        provider: cipher.encrypt(key.encode()).decode() if key else ''
        for provider, key in decrypted_existing.items()
    }
    
    save_user_data(user_id, user_data)
    return jsonify({"success": True})

@app.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations():
    user_id = session['user_id']
    user_data = load_user_data(user_id)
    convos = user_data.get('conversations', {})
    
    result = [
        {"id": k, "title": v["title"], "timestamp": v["timestamp"], "provider": v["provider"], "model": v["model"]}
        for k, v in convos.items()
    ]
    return jsonify(sorted(result, key=lambda x: x["timestamp"], reverse=True))

@app.route('/api/conversations', methods=['POST'])
@login_required
def create_conversation():
    user_id = session['user_id']
    user_data = load_user_data(user_id)
    
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
    
    save_user_data(user_id, user_data)
    return jsonify({"id": conv_id})

@app.route('/api/conversations/<conv_id>', methods=['GET'])
@login_required
def get_conversation(conv_id):
    user_id = session['user_id']
    user_data = load_user_data(user_id)
    convos = user_data.get('conversations', {})
    
    if conv_id in convos:
        return jsonify(convos[conv_id])
    return jsonify({"error": "Conversation not found"}), 404

@app.route('/api/conversations/<conv_id>', methods=['DELETE'])
@login_required
def delete_conversation(conv_id):
    user_id = session['user_id']
    user_data = load_user_data(user_id)
    
    if conv_id in user_data.get('conversations', {}):
        del user_data['conversations'][conv_id]
        save_user_data(user_id, user_data)
        return jsonify({"success": True})
    return jsonify({"error": "Conversation not found"}), 404


@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    user_id = session['user_id']
    user_data = load_user_data(user_id)
    
    data = request.json
    user_message = data.get("message")
    provider = data.get("provider", "openai")
    model = data.get("model", "gpt-4o")
    conv_id = data.get("conversation_id")
    
    api_key = get_api_key(provider)
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
        result = generate_response(provider, model, conv["messages"], api_key)
        
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
        save_user_data(user_id, user_data)
        
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
        save_user_data(user_id, user_data)
        
        return jsonify({
            "error": str(e),
            "conversation_id": conv_id,
            "provider": provider,
            "model": model
        }), 500


def calculate_cost(provider, model, input_tokens, output_tokens):
    """Calculate cost based on token usage"""
    if provider not in MODELS or model not in MODELS[provider].get("pricing", {}):
        return 0.0
    
    pricing = MODELS[provider]["pricing"][model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


def generate_response(provider, model, messages, api_key):
    """Generate response and return content with token usage"""
    if provider == "openai":
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages]
        )
        return {
            "content": response.choices[0].message.content,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    
    elif provider == "anthropic":
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages]
        )
        return {
            "content": response.content[0].text,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
        }
    
    elif provider == "google":
        genai.configure(api_key=api_key)
        genai_model = genai.GenerativeModel(f'models/{model}')
        
        chat = genai_model.start_chat(history=[])
        for msg in messages[:-1]:
            if msg["role"] == "user":
                chat.send_message(msg["content"])
        
        response = chat.send_message(messages[-1]["content"])
        
        # Google provides token counts in the response
        input_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0
        output_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0
        
        return {
            "content": response.text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
    
    else:
        raise ValueError(f"Unknown provider: {provider}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
