import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Import AI SDKs
import openai
import anthropic
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)

# Configure Clients
client_openai = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get("message")
    selected_model = data.get("model")

    try:
        # --- ROUTING LOGIC ---
        if selected_model == "gpt-4o":
            response = client_openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": user_message}]
            )
            bot_response = response.choices[0].message.content

        elif selected_model == "claude-3-sonnet":
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
