"""AI provider service"""
import openai
import anthropic
import google.generativeai as genai


class AIService:
    @staticmethod
    def generate_response(provider, model, messages, api_key):
        """Generate response and return content with token usage"""
        if provider == "openai":
            return AIService._openai_response(model, messages, api_key)
        elif provider == "anthropic":
            return AIService._anthropic_response(model, messages, api_key)
        elif provider == "google":
            return AIService._google_response(model, messages, api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    @staticmethod
    def _openai_response(model, messages, api_key):
        """Get OpenAI response"""
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
    
    @staticmethod
    def _anthropic_response(model, messages, api_key):
        """Get Anthropic response"""
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
    
    @staticmethod
    def _google_response(model, messages, api_key):
        """Get Google response"""
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
