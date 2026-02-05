import os
import uuid
import json
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from datetime import datetime
from cryptography.fernet import Fernet
import base64
import hashlib

# Import AI SDKs
import openai
import anthropic
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# Encryption key for API keys (in production, use a proper secret management)
def get_encryption_key():
    secret = app.secret_key if isinstance(app.secret_key, bytes) else app.secret_key.encode()
    key = hashlib.sha256(secret).digest()
    return base64.urlsafe_b64encode(key)

cipher = Fernet(get_encryption_key())

# File to store encrypted API keys
API_KEYS_FILE = 'api_keys.json'

def load_api_keys():
    """Load and decrypt API keys from file"""
    if os.path.exists(API_KEYS_FILE):
        try:
            with open(API_KEYS_FILE, 'r') as f:
                encrypted_keys = json.load(f)
            return {
                provider: cipher.decrypt(key.encode()).decode() if key else ""
                for provider, key in encrypted_keys.items()
            }
        except Exception:
            return {"openai": "", "anthropic": "", "google": ""}
    return {"openai": "", "anthropic": "", "google": ""}

def save_api_keys(keys):
    """Encrypt and save API keys to file"""
    encrypted_keys = {
        provider: cipher.encrypt(key.encode()).decode() if key else ""
        for provider, key in keys.items()
    }
    with open(API_KEYS_FILE, 'w') as f:
        json.dump(encrypted_keys, f)

def get_api_key(provider):
    """Get API key for provider - from session, file, or env"""
    # First check session (user-provided keys)
    session_keys = session.get('api_keys', {})
    if session_keys.get(provider):
        return session_keys[provider]
    
    # Then check saved file
    saved_keys = load_api_keys()
    if saved_keys.get(provider):
        return saved_keys[provider]
    
    # Finally fall back to environment variables
    env_map = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY', 
        'google': 'GEMINI_API_KEY'
    }
    return os.getenv(env_map.get(provider, ''), '')

# Model configurations
MODELS = {
    "openai": {
        "name": "OpenAI",
        "models": {
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini",
            "gpt-4-turbo": "GPT-4 Turbo",
            "gpt-3.5-turbo": "GPT-3.5 Turbo"
        }
    },
    "anthropic": {
        "name": "Anthropic",
        "models": {
            "claude-sonnet-4-20250514": "Claude Sonnet 4",
            "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
            "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
            "claude-3-opus-20240229": "Claude 3 Opus"
        }
    },
    "google": {
        "name": "Google",
        "models": {
            "gemini-2.5-flash": "Gemini 2.5 Flash",
            "gemini-2.5-pro": "Gemini 2.5 Pro",
            "gemini-2.0-flash": "Gemini 2.0 Flash",
            "gemini-1.5-pro": "Gemini 1.5 Pro"
        }
    }
}

# In-memory conversation storage
conversations = {}

@app.route('/')
def index():
    return render_template('index.html', models=MODELS)

@app.route('/api/models', methods=['GET'])
def get_models():
    return jsonify(MODELS)

@app.route('/api/keys', methods=['GET'])
def get_keys_status():
    """Get status of which API keys are configured (not the actual keys)"""
    status = {}
    for provider in ['openai', 'anthropic', 'google']:
        key = get_api_key(provider)
        status[provider] = {
            'configured': bool(key),
            'masked': f"{'*' * 20}...{key[-4:]}" if key and len(key) > 4 else ""
        }
    return jsonify(status)

@app.route('/api/keys', methods=['POST'])
def save_keys():
    """Save API keys - merges with existing keys"""
    data = request.json
    
    # Load existing keys first
    existing_keys = load_api_keys()
    
    # Only update keys that were provided (non-empty)
    updated_keys = {
        'openai': data.get('openai', '').strip() or existing_keys.get('openai', ''),
        'anthropic': data.get('anthropic', '').strip() or existing_keys.get('anthropic', ''),
        'google': data.get('google', '').strip() or existing_keys.get('google', '')
    }
    
    # Save to file (persistent)
    if data.get('persist', True):
        save_api_keys(updated_keys)
    
    # Also store in session for immediate use
    session['api_keys'] = updated_keys
    
    return jsonify({"success": True})

@app.route('/api/keys/test', methods=['POST'])
def test_key():
    """Test if an API key is valid"""
    data = request.json
    provider = data.get('provider')
    key = data.get('key')
    
    try:
        if provider == 'openai':
            client = openai.OpenAI(api_key=key)
            client.models.list()
        elif provider == 'anthropic':
            client = anthropic.Anthropic(api_key=key)
            client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
        elif provider == 'google':
            genai.configure(api_key=key)
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            model.generate_content("Hi")
        
        return jsonify({"valid": True})
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)})


@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    session_id = session.get('session_id')
    if not session_id:
        session['session_id'] = str(uuid.uuid4())
        return jsonify([])
    
    user_convos = [
        {"id": k, "title": v["title"], "timestamp": v["timestamp"], "provider": v["provider"], "model": v["model"]}
        for k, v in conversations.items() 
        if v.get("session_id") == session_id
    ]
    return jsonify(sorted(user_convos, key=lambda x: x["timestamp"], reverse=True))

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    data = request.json
    conv_id = str(uuid.uuid4())
    conversations[conv_id] = {
        "id": conv_id,
        "session_id": session['session_id'],
        "title": "New Chat",
        "messages": [],
        "provider": data.get("provider", "openai"),
        "model": data.get("model", "gpt-4o"),
        "timestamp": datetime.now().isoformat()
    }
    return jsonify({"id": conv_id})

@app.route('/api/conversations/<conv_id>', methods=['GET'])
def get_conversation(conv_id):
    if conv_id in conversations:
        return jsonify(conversations[conv_id])
    return jsonify({"error": "Conversation not found"}), 404

@app.route('/api/conversations/<conv_id>', methods=['DELETE'])
def delete_conversation(conv_id):
    if conv_id in conversations:
        del conversations[conv_id]
        return jsonify({"success": True})
    return jsonify({"error": "Conversation not found"}), 404

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get("message")
    provider = data.get("provider", "openai")
    model = data.get("model", "gpt-4o")
    conv_id = data.get("conversation_id")
    
    # Check if API key is configured
    api_key = get_api_key(provider)
    if not api_key:
        return jsonify({"error": f"API key not configured for {MODELS[provider]['name']}. Please add your API key in Settings."}), 400
    
    # Get or create conversation
    if conv_id and conv_id in conversations:
        conv = conversations[conv_id]
        # Update the current provider/model for this conversation
        conv["provider"] = provider
        conv["model"] = model
    else:
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        conv_id = str(uuid.uuid4())
        conversations[conv_id] = {
            "id": conv_id,
            "session_id": session['session_id'],
            "title": user_message[:50] + "..." if len(user_message) > 50 else user_message,
            "messages": [],
            "provider": provider,
            "model": model,
            "timestamp": datetime.now().isoformat()
        }
        conv = conversations[conv_id]
    
    # Add user message with metadata
    conv["messages"].append({
        "role": "user", 
        "content": user_message
    })
    
    if len(conv["messages"]) == 1:
        conv["title"] = user_message[:50] + "..." if len(user_message) > 50 else user_message

    try:
        bot_response = generate_response(provider, model, conv["messages"], api_key)
        # Add assistant message with provider/model info
        conv["messages"].append({
            "role": "assistant", 
            "content": bot_response,
            "provider": provider,
            "model": model
        })
        conv["timestamp"] = datetime.now().isoformat()
        
        return jsonify({
            "response": bot_response,
            "conversation_id": conv_id,
            "provider": provider,
            "model": model
        })

    except Exception as e:
        error_message = f"Error: {str(e)}"
        # Store the error in conversation history
        conv["messages"].append({
            "role": "assistant",
            "content": error_message,
            "provider": provider,
            "model": model,
            "is_error": True
        })
        conv["timestamp"] = datetime.now().isoformat()
        
        return jsonify({
            "error": str(e),
            "conversation_id": conv_id,
            "provider": provider,
            "model": model
        }), 500


def generate_response(provider, model, messages, api_key):
    """Generate response based on provider and model"""
    
    if provider == "openai":
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages]
        )
        return response.choices[0].message.content
    
    elif provider == "anthropic":
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages]
        )
        return response.content[0].text
    
    elif provider == "google":
        genai.configure(api_key=api_key)
        genai_model = genai.GenerativeModel(f'models/{model}')
        
        chat = genai_model.start_chat(history=[])
        for msg in messages[:-1]:
            if msg["role"] == "user":
                chat.send_message(msg["content"])
        
        response = chat.send_message(messages[-1]["content"])
        return response.text
    
    else:
        raise ValueError(f"Unknown provider: {provider}")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
