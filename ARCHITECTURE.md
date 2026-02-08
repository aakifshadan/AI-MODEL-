# Application Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser                              │
│                    (HTML/CSS/JavaScript)                     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP Requests
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Flask Application                       │
│                         (app.py)                             │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Auth       │  │    Chat      │  │     API      │
│   Routes     │  │   Routes     │  │   Routes     │
│ (auth.py)    │  │  (chat.py)   │  │  (api.py)    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    User      │  │      AI      │  │   Models     │
│   Service    │  │   Service    │  │  (pricing)   │
│(user_svc.py) │  │ (ai_svc.py)  │  │(pricing.py)  │
└──────┬───────┘  └──────┬───────┘  └──────────────┘
       │                 │
       │                 │
       ▼                 ▼
┌──────────────┐  ┌──────────────────────────────┐
│  JSON Files  │  │    AI Provider APIs          │
│  (users,     │  │  ┌────────┬─────────┬──────┐ │
│   data)      │  │  │ OpenAI │Anthropic│Google│ │
└──────────────┘  │  └────────┴─────────┴──────┘ │
                  └──────────────────────────────┘
```

## Request Flow

### 1. User Authentication
```
Browser → /auth/login → auth.py → UserService → users.json
                                      ↓
                                   Session
```

### 2. Chat Message
```
Browser → /api/chat → chat.py → UserService (get API key)
                         ↓
                    AIService (generate response)
                         ↓
                    OpenAI/Anthropic/Google API
                         ↓
                    pricing.py (calculate cost)
                         ↓
                    UserService (save conversation)
                         ↓
                    Response with tokens & cost
```

### 3. API Key Management
```
Browser → /api/keys → api.py → UserService (encrypt & save)
                                    ↓
                              user_data/*.json
```

## Layer Responsibilities

### Presentation Layer (Routes)
**Files:** `routes/auth.py`, `routes/chat.py`, `routes/api.py`

**Responsibilities:**
- Handle HTTP requests/responses
- Validate input
- Call service layer
- Return JSON/HTML

**Does NOT:**
- Access database directly
- Contain business logic
- Call external APIs

### Business Logic Layer (Services)
**Files:** `services/user_service.py`, `services/ai_service.py`

**Responsibilities:**
- Implement business logic
- Manage data persistence
- Integrate with external APIs
- Handle encryption/security

**Does NOT:**
- Know about HTTP
- Handle request/response
- Render templates

### Data Layer (Models)
**Files:** `models/pricing.py`

**Responsibilities:**
- Define data structures
- Pricing calculations
- Pure functions

**Does NOT:**
- Access database
- Call external APIs
- Handle HTTP

## Component Details

### UserService
```python
class UserService:
    - load_users()           # Load all users
    - save_users()           # Save all users
    - load_user_data()       # Load user-specific data
    - save_user_data()       # Save user-specific data
    - get_api_key()          # Get encrypted API key
    - save_api_keys()        # Save encrypted API keys
```

### AIService
```python
class AIService:
    - generate_response()    # Main entry point
    - _openai_response()     # OpenAI integration
    - _anthropic_response()  # Anthropic integration
    - _google_response()     # Google integration
```

### Pricing Model
```python
MODELS = {
    "openai": {...},
    "anthropic": {...},
    "google": {...}
}

calculate_cost(provider, model, input_tokens, output_tokens)
```

## Data Flow

### Conversation Storage
```
User sends message
    ↓
chat.py receives request
    ↓
UserService.load_user_data(user_id)
    ↓
AIService.generate_response(...)
    ↓
calculate_cost(...)
    ↓
UserService.save_user_data(user_id, updated_data)
    ↓
Response sent to browser
```

### API Key Encryption
```
User enters API key
    ↓
api.py receives key
    ↓
UserService.save_api_keys(user_id, keys)
    ↓
Encrypt with Fernet cipher
    ↓
Save to user_data/{user_id}.json
```

## Security

### Authentication
- Session-based authentication
- OAuth 2.0 for Google login
- Password hashing with pbkdf2:sha256

### API Key Storage
- Encrypted with Fernet (symmetric encryption)
- Key derived from Flask secret key
- Stored per-user in separate files

### Data Isolation
- Each user has separate data file
- Session validates user access
- No cross-user data leakage

## Configuration

### Environment Variables (.env)
```
FLASK_SECRET_KEY=...        # Session & encryption
GOOGLE_CLIENT_ID=...        # OAuth
GOOGLE_CLIENT_SECRET=...    # OAuth
OPENAI_API_KEY=...          # Fallback
ANTHROPIC_API_KEY=...       # Fallback
GEMINI_API_KEY=...          # Fallback
```

### Config Class (config.py)
```python
class Config:
    SECRET_KEY              # From env
    GOOGLE_CLIENT_ID        # From env
    GOOGLE_CLIENT_SECRET    # From env
    USERS_FILE             # users.json
    USER_DATA_DIR          # user_data/
    DEBUG                  # True
    HOST                   # 0.0.0.0
    PORT                   # 5000
```

## Scalability Considerations

### Current (JSON Files)
- ✅ Simple
- ✅ No dependencies
- ❌ Not suitable for high traffic
- ❌ No concurrent access control

### Future (Database)
- ✅ Concurrent access
- ✅ ACID transactions
- ✅ Better performance
- ✅ Easier querying

### Migration Path
1. Keep service interfaces the same
2. Replace JSON operations with SQLAlchemy
3. No changes to routes needed
4. Services abstract the storage layer

## Testing Strategy

### Unit Tests
```
services/
  ├── test_user_service.py
  └── test_ai_service.py

models/
  └── test_pricing.py
```

### Integration Tests
```
routes/
  ├── test_auth.py
  ├── test_chat.py
  └── test_api.py
```

### End-to-End Tests
```
tests/
  └── test_e2e.py
```

## Deployment

### Development
```bash
python app.py
```

### Production
```bash
gunicorn "app:create_app()" \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --timeout 120
```

### Docker
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "app:create_app()", "--bind", "0.0.0.0:5000"]
```

## Monitoring

### Logs
- Flask debug logs
- Service-level logging
- Error tracking

### Metrics
- Request count
- Response time
- Token usage
- Cost tracking

### Health Checks
```python
@app.route('/health')
def health():
    return {'status': 'healthy'}
```

## Future Enhancements

1. **Caching Layer**
   - Redis for session storage
   - Cache frequent queries

2. **Rate Limiting**
   - Per-user limits
   - Per-provider limits

3. **Background Jobs**
   - Celery for async tasks
   - Email notifications

4. **WebSockets**
   - Real-time streaming
   - Live token updates

5. **Multi-tenancy**
   - Organization support
   - Team collaboration
