import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Import AI SDKs
#import openai
import anthropic
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)


# ===== HISTORY FEATURE (BACKEND ONLY) =====
HISTORY_FILE = "chat_history.json"

def save_history(user_message, model, bot_response):
    history = []

    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)

    history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": model,
        "user": user_message,
        "bot": bot_response
    })

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)


# Configure Clients
#client_openai = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():

           save_history(user_message, selected_model, bot_response)

# ===== GET HISTORY API (ADDED) =====
@app.route('/history', methods=['GET'])
def get_history():
    if not os.path.exists(HISTORY_FILE):
        return jsonify([])

    with open(HISTORY_FILE, "r") as f:
        return jsonify(json.load(f))

    try:
        # --- ROUTING LOGIC ---
        # if selected_model == "gpt-4o":
        #     response = client_openai.chat.completions.create(
        #         model="gpt-4o",
        #         messages=[{"role": "user", "content": user_message}]
        #     )
        #     bot_response = response.choices[0].message.content

        if selected_model == "claude-3-sonnet":
            response = client_claude.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1024,
                messages=[{"role": "user", "content": user_message}]
            )
            bot_response = response.content[0].text

        elif selected_model == "gemini-2.5-flash":
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            response = model.generate_content(user_message)
            bot_response = response.text

        else:
            bot_response = "Error: Invalid model selected."

        return jsonify({"response": bot_response})

    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)