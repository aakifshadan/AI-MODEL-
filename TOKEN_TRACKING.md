# Token Tracking Implementation

## Overview
Token usage and cost tracking is now displayed in the **Provider/Model selector area** in the sidebar with a clean, minimal design.

## Location
The usage stats appear in the left sidebar, directly below the Model selector dropdown, showing:
- **Tokens**: Total tokens used across all conversations
- **Cost**: Total cost in USD

## Features
- Updates in real-time after each AI response
- Persists across sessions (loads from conversation history)
- Clean, minimal UI that doesn't clutter the chat interface
- Monospace font for numbers (easier to read)
- Cost displayed in green accent color

## How It Works
1. When you send a message, the AI response includes token usage data
2. The sidebar stats automatically increment with the new usage
3. On page load, it calculates total usage from all your conversations
4. All data is stored with each message in your conversation history

## Pricing (per 1M tokens)

### OpenAI
- GPT-4o: $2.50 input / $10.00 output
- GPT-4o Mini: $0.15 input / $0.60 output
- GPT-4 Turbo: $10.00 input / $30.00 output
- GPT-3.5 Turbo: $0.50 input / $1.50 output

### Anthropic (Claude)
- Claude Sonnet 4: $3.00 input / $15.00 output
- Claude 3.5 Sonnet: $3.00 input / $15.00 output
- Claude 3.5 Haiku: $0.80 input / $4.00 output
- Claude 3 Opus: $15.00 input / $75.00 output

### Google (Gemini)
- Gemini 2.5 Flash: $0.10 input / $0.40 output
- Gemini 2.5 Pro: $1.25 input / $5.00 output
- Gemini 2.0 Flash: $0.10 input / $0.40 output
- Gemini 1.5 Pro: $1.25 input / $5.00 output

## Note on "Tokens Left"

API providers (OpenAI, Anthropic, Google) don't expose "remaining tokens" because they work on a billing model, not a quota system. You're charged for what you use, and there's no hard limit unless you set one in your API dashboard.

To monitor your spending and set limits:
- OpenAI: https://platform.openai.com/usage
- Anthropic: https://console.anthropic.com/settings/billing
- Google: https://console.cloud.google.com/billing

