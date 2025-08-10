# Development Guide

## Prerequisites

- Docker and Docker Compose
- Google Gemini API key
- Git

## Quick Development Setup

```bash
git clone https://github.com/yingzha/multimodal-scout.git
cd multimodal-scout
echo "GOOGLE_API_KEY=your_api_key_here" > .env
docker-compose up -d
```

## Development Workflow

### Making Changes

**Backend changes:**
- Edit files in `src/backend/`
- Changes auto-reload thanks to volume mounts

**Frontend changes:**
- Edit files in `src/frontend/app/`
- Changes auto-reload in development mode

**Database changes:**
1. Modify models in `src/backend/database.py`
2. Create migration: `docker-compose exec backend alembic revision --autogenerate -m "Description"`
3. Apply migration: `docker-compose exec backend alembic upgrade head`

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Database Access

```bash
docker-compose exec postgres psql -U scout_user -d multimodal_scout
```

### Rebuilding Containers

```bash
# After dependency changes
docker-compose build

# Clean rebuild
docker-compose down
docker-compose up -d --build
```

## Testing

### Backend Tests

```bash
# Run all backend tests
docker-compose run --rm backend uv run python tests/backend/test_app.py
docker-compose run --rm backend uv run python tests/backend/test_database.py
docker-compose run --rm backend uv run python tests/backend/test_pipeline.py
docker-compose run --rm backend uv run python tests/backend/test_search.py
docker-compose run --rm backend uv run python tests/backend/test_scrapers.py

# Run with pytest (after adding pytest to dependencies)
docker-compose run --rm backend uv add --dev pytest
docker-compose run --rm backend uv run pytest tests/backend/
```

### Frontend Tests

```bash
# Build test
docker-compose exec frontend npm run build

# Type checking
docker-compose exec frontend npx tsc --noEmit
```

### Integration Tests

```bash
# Test API endpoints
curl -s http://localhost:8000/api/topics
curl -s -X POST "http://localhost:8000/api/fetch" \
  -H "Content-Type: application/json" \
  -d '{"selectedDays": 1, "maxResults": 2, "topics": ["ai"], "researchRatio": 0.5}'

# Test frontend-backend connectivity
curl -s -I http://localhost:3000
```

That's it! Docker handles all the environment complexity.