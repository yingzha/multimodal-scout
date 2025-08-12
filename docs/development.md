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
docker-compose logs -f cron

# Cron job monitoring
docker-compose logs cron --tail=50
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
docker-compose run --rm backend pytest tests/backend/
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

# Test bookmarks functionality
curl -s http://localhost:8000/api/bookmarks
curl -s -X POST "http://localhost:8000/api/bookmarks" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "link": "http://example.com", "source": "Test", "summary": "Test summary"}'

# Test summary editing
curl -s -X PUT "http://localhost:8000/api/bookmarks/summary?link=http%3A//example.com&summary=Updated%20summary"

# Test frontend-backend connectivity
curl -s -I http://localhost:3000
```

## New Features

### Summary Editing
- Users can edit bookmark summaries inline by clicking the ✏️ icon
- Edited summaries are marked with "User edited" badge
- Edited summaries are prioritized in fetch results over cached summaries

### Automated Scraping
- **Production-ready cron jobs**: Docker-based scheduled tasks with proper environment isolation
- **Reliable execution**: Fixed environment variable inheritance and database connectivity issues
- **Comprehensive logging**: Detailed monitoring with timestamps, performance metrics, and visual indicators
- **Hacker News**: Scraped every hour (0 * * * *) with automatic content processing
- **Hugging Face papers**: Collected every 6 hours (0 */6 * * *) with trending paper detection
- **Automatic AI processing**: Summary generation and database caching for all new content

#### Cron Job Management
```bash
# Check cron job status
docker-compose exec cron crontab -l

# Test individual scrapers manually
docker-compose exec cron /app/cron_env.sh /root/.local/bin/uv run python -m src.backend.run_scraper backend.scraper.scrape_hacker_news

# Monitor cron job execution
docker-compose logs cron -f

# Restart cron service
docker-compose restart cron
```

### Upload Custom Links
- Users can upload any URL to be processed and bookmarked
- Automatic content categorization (Research/Industry/General)
- Smart summary generation

### Cache Management
```bash
# View cache statistics
docker-compose exec backend python -m src.backend.cache_manager stats

# Cleanup old cache entries
docker-compose exec backend python -m src.backend.cache_manager cleanup
```

That's it! Docker handles all the environment complexity.
