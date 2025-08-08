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

```bash
# Backend tests
docker-compose exec backend pytest

# Frontend build test
docker-compose exec frontend npm run build
```

That's it! Docker handles all the environment complexity.