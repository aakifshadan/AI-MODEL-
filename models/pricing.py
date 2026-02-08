"""Model configurations and pricing"""

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


def calculate_cost(provider, model, input_tokens, output_tokens):
    """Calculate cost based on token usage"""
    if provider not in MODELS or model not in MODELS[provider].get("pricing", {}):
        return 0.0
    
    pricing = MODELS[provider]["pricing"][model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost
