# HealthGuard AI Backend

This is the FastAPI backend for HealthGuard AI, a personal health assistant system for insulin resistance management.

## Requirements

- Python 3.10+
- FastAPI
- See `requirements.txt` for full list

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m app.main
# or
uvicorn app.main:app --reload
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Architecture

- `app/storage/` - Storage interface and implementations (Local, S3, OSS)
- `app/core/` - Core business logic (MemoryManager)
- `app/models/` - Pydantic models for data validation
- `app/api/` - API endpoints (auth, chat, health)
- `app/agents/` - AI agents (Router, Diet, Fitness, Medical)
- `app/utils/` - Utility functions (auth, helpers)
- `app/config/` - Configuration settings

## Environment Variables

Create a `.env` file in the backend directory:

```env
SECRET_KEY=your-secret-key-here
DEBUG=true
OPENAI_API_KEY=your-openai-key
WEB_SEARCH_API_KEY=your-search-api-key
```

## Data Storage

Data is stored in the `data/` directory by default:
- `data/users/{user_id}/memories/daily_logs/` - Daily logs
- `data/users/{user_id}/medical/records/` - Medical records
- `data/users/{user_id}/raw_chats/` - Chat logs
