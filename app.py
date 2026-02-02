import os
import uuid
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from datetime import datetime

# Import AI SDKs
import openai
import anthropic
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure Clients
client_openai = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Model configurations with sub-models
MODELS = {
    "openai": {
        "name": "OpenAI",
        "icon": "🤖",
        "models": {
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini",
            "gpt-4-turbo": "GPT-4 Turbo",
            "gpt-3.5-turbo": "GPT-3.5 Turbo"
        }
    },
    "anthropic": {
        "name": "Anthropic",
        "icon": "🧠",
        "models": {
            "claude-sonnet-4-20250514": "Claude Sonnet 4",
            "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
            "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
            "claude-3-opus-20240229": "Claude 3 Opus"
        }
    },
    "google": {
        "name": "Google",
        "icon": "✨",
        "models": {
            "gemini-2.5-flash": "Gemini 2.5 Flash",
            "gemini-2.5-pro": "Gemini 2.5 Pro",
            "gemini-2.0-flash": "Gemini 2.0 Flash",
            "gemini-1.5-pro": "Gemini 1.5 Pro"
        }
    }
}

# In-memory conversation storage (use database in production)
conversations = {}

@app.route('/')
def index():
    return render_template('index.html', models=MODELS)

@app.route('/api/models', methods=['GET'])
def get_models():
    return jsonify(MODELS)

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
    
    # Get or create conversation
    if conv_id and conv_id in conversations:
        conv = conversations[conv_id]
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
    
    # Add user message to history
    conv["messages"].append({"role": "user", "content": user_message})
    
    # Update title if first message
    if len(conv["messages"]) == 1:
        conv["title"] = user_message[:50] + "..." if len(user_message) > 50 else user_message

    try:
        bot_response = generate_response(provider, model, conv["messages"])
        conv["messages"].append({"role": "assistant", "content": bot_response})
        conv["timestamp"] = datetime.now().isoformat()
        
        return jsonify({
            "response": bot_response,
            "conversation_id": conv_id
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def generate_response(provider, model, messages):
    """Generate response based on provider and model"""
    
    if provider == "openai":
        response = client_openai.chat.completions.create(
            model=model,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages]
        )
        return response.choices[0].message.content
    
    elif provider == "anthropic":
        # Anthropic requires system message separately
        response = client_claude.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages]
        )
        return response.content[0].text
    
    elif provider == "google":
        genai_model = genai.GenerativeModel(f'models/{model}')
        
        # Convert messages to Gemini format
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
