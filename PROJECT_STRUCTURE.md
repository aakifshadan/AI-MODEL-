# Project Structure

## Overview
The application has been refactored from a monolithic structure into a modular, maintainable architecture following Flask best practices.

## Directory Structure

```
AI-MODEL-/
├── app_new.py              # Main entry point (NEW - use this)
├── app.py                  # Old monolithic file (can be removed)
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
├── .gitignore
│
├── models/                 # Data models and business logic
│   ├── __init__.py
│   └── pricing.py          # Model pricing and cost calculation
│
├── routes/                 # Route handlers (controllers)
│   ├── __init__.py
│   ├── auth.py             # Authentication routes
│   ├── chat.py             # Chat functionality routes
│   └── api.py              # API endpoints
│
├── services/               # Business logic layer
│   ├── __init__.py
│   ├── user_service.py     # User management
│   └── ai_service.py       # AI provider integration
│
├── static/                 # Static assets (future)
│   ├── css/
│   └── js/
│
├── templates/              # HTML templates
│   ├── base.html           # Base template (future)
│   ├── index.html          # Main chat interface
│   └── login.html          # Login page
│
└── user_data/              # User data storage
    └── *.json              # Individual user files
```

## Architecture Layers

### 1. Configuration (`config.py`)
- Centralized configuration management
- Environment variable loading
- Application settings

### 2. Models (`models/`)
- **pricing.py**: Model definitions, pricing data, cost calculations
- Pure data and business logic, no Flask dependencies

### 3. Services (`services/`)
- **user_service.py**: User management, authentication, data persistence
- **ai_service.py**: AI provider integration (OpenAI, Anthropic, Google)
- Reusable business logic independent of routes

### 4. Routes (`routes/`)
- **auth.py**: Login, register, OAuth, logout
- **chat.py**: Main chat interface and message handling
- **api.py**: REST API endpoints for frontend
- Thin controllers that delegate to services

### 5. Application Factory (`app_new.py`)
- Creates and configures Flask app
- Initializes services
- Registers blueprints
- Clean entry point

## Benefits of New Structure

### Separation of Concerns
- Each module has a single responsibility
- Easy to locate and modify specific functionality

### Testability
- Services can be tested independently
- Mock dependencies easily
- Unit tests for business logic

### Maintainability
- Smaller, focused files
- Clear dependencies
- Easy to understand flow

### Scalability
- Add new providers by extending `ai_service.py`
- Add new routes without touching existing code
- Easy to add new features

### Reusability
- Services can be used across different routes
- Models can be imported anywhere
- Configuration centralized

## Migration Guide

### To use the new structure:

1. **Test the new app:**
   ```bash
   python app_new.py
   ```

2. **Once verified, rename files:**
   ```bash
   mv app.py app_old.py
   mv app_new.py app.py
   ```

3. **Update any deployment scripts** to use the new structure

### Key Changes:

- **Old**: Everything in `app.py` (600+ lines)
- **New**: Modular structure with clear separation

- **Old**: Direct function calls
- **New**: Service layer with dependency injection

- **Old**: Mixed concerns (auth, chat, AI, data)
- **New**: Each concern in its own module

## Future Improvements

### Static Assets
Move CSS and JavaScript to `static/` folder:
- Extract inline styles to `static/css/style.css`
- Extract inline JS to `static/js/app.js`

### Base Template
Create `templates/base.html` for shared layout:
- Common HTML structure
- Shared CSS/JS includes
- Template inheritance

### Database
Replace JSON files with proper database:
- SQLAlchemy for ORM
- PostgreSQL or SQLite
- Proper migrations

### Testing
Add test suite:
- Unit tests for services
- Integration tests for routes
- End-to-end tests

### API Documentation
Add API documentation:
- OpenAPI/Swagger spec
- Auto-generated docs
- Request/response examples

## Running the Application

### Development
```bash
python app_new.py
```

### Production
```bash
gunicorn "app_new:create_app()" --bind 0.0.0.0:5000
```

## Environment Variables

Required in `.env`:
```
FLASK_SECRET_KEY=your-secret-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

Optional (fallback API keys):
```
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GEMINI_API_KEY=your-gemini-key
```
