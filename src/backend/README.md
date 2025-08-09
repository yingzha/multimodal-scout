# Multimodal Scout Backend

A Python-based content scouting system that scrapes, summarizes, and filters sources from Hacker News and Hugging Face using AI-powered summarization and semantic search.

## Features

- **Multi-source scraping**: Hacker News stories and Hugging Face trending papers
- **AI-powered summarization**: Generates summaries using Google's API
- **Intelligent filtering**: Keyword and semantic search capabilities
- **Scalable caching**: PostgreSQL database with fallback to JSON
- **Date-based queries**: Search and manage summaries by creation date
- **Cache management**: Built-in tools for cleanup and analytics

## Quick Start with Docker

### Prerequisites

- Docker and Docker Compose installed
- Google API key for summary generation

### Setup

```bash
# Clone and navigate to project
cd multimodal-scout

# Set up environment variables
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# Start services (builds dependencies automatically)
docker-compose up -d

# Check logs
docker-compose logs -f backend
```

That's it! Docker automatically:
- Installs all Python dependencies using uv
- Sets up PostgreSQL database
- Runs database migrations
- Starts the application

## Usage Examples

### Cache Management

```bash
# View cache statistics
docker-compose exec backend python -m src.backend.cache_manager stats

# Search summaries by content
docker-compose exec backend python -m src.backend.cache_manager search --query "AI" --limit 5

# View recent summaries
docker-compose exec backend python -m src.backend.cache_manager recent --days 7

# Clean up old summaries (older than 30 days)
docker-compose exec backend python -m src.backend.cache_manager cleanup --days 30

# Migrate existing JSON cache to database
docker-compose exec backend python -m src.backend.cache_manager migrate
```

### Database Operations

```bash
# Connect to PostgreSQL directly
docker-compose exec postgres psql -U scout_user -d multimodal_scout

# Run database migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "Add new feature"

# View migration history
docker-compose exec backend alembic history
```

### Development Commands

```bash
# Run one-off commands
docker-compose exec backend python -m src.backend.scraper

# Access container shell for debugging
docker-compose exec backend bash

# View real-time logs
docker-compose logs -f backend

# Restart specific service
docker-compose restart backend
```

## Docker Management

### Basic Operations

```bash
# Start services in background
docker-compose up -d

# Start services with live logs
docker-compose up

# Stop services
docker-compose down

# Stop and remove all data (destructive)
docker-compose down -v

# Rebuild after code changes
docker-compose up --build -d
```

### Troubleshooting

```bash
# Check service status
docker-compose ps

# View detailed logs
docker-compose logs backend --tail=50

# Restart all services
docker-compose restart

# Reset everything (destructive)
docker-compose down -v
docker-compose up --build
```

## Configuration

### Environment Variables

Create `.env` file with:
```bash
DATABASE_URL=postgresql://scout_user:scout_password@postgres:5432/multimodal_scout
GOOGLE_API_KEY=your_google_api_key_here
DEBUG=false
```

### Keywords Configuration

Edit `src/backend/constants.py` to modify filtering keywords:

```python
INTERESTED_KEYWORDS = [
    "artificial intelligence", "machine learning", "deep learning",
    # Add your keywords here
]
```

## Architecture

### Docker Services

- **postgres**: PostgreSQL 15 database with persistent storage
- **backend**: Main application container using uv for fast dependency management

### Core Components

- **`merger.py`**: Main pipeline orchestration
- **`scraper.py`**: Web scraping for sources
- **`search.py`**: Keyword and semantic search
- **`cache.py`**: Caching interface with database/JSON fallback
- **`db_cache.py`**: PostgreSQL database operations
- **`cache_manager.py`**: CLI cache management tool

### Data Flow

1. **Scraping**: Collect sources from multiple platforms
2. **Enrichment**: Generate AI summaries (cached in PostgreSQL)
3. **Filtering**: Apply keyword and semantic search
4. **Storage**: Persist results with date indexing
5. **Management**: Cleanup and analytics via CLI tools

## Example Workflows

### Daily Operation

```bash
# Start the system
docker-compose up -d

# Check what's been processed
docker-compose exec backend python -m src.backend.cache_manager stats

# Search for specific topics
docker-compose exec backend python -m src.backend.cache_manager search --query "machine learning"

# View recent activity
docker-compose exec backend python -m src.backend.cache_manager recent --days 3
```

### Weekly Maintenance

```bash
# Clean up old data
docker-compose exec backend python -m src.backend.cache_manager cleanup --days 30

# Check system health
docker-compose ps
docker-compose logs backend --tail=20

# Update and restart
git pull
docker-compose up --build -d
```

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U scout_user multimodal_scout > backup_$(date +%Y%m%d).sql

# Restore backup (destructive)
docker-compose exec postgres psql -U scout_user multimodal_scout < backup_20250807.sql
```

## Development Notes

- Dependencies are managed with `uv` and automatically installed in Docker
- Code changes are reflected immediately via volume mounts
- Database data persists between container restarts
- All Python dependencies are locked in `uv.lock` for reproducible builds

## No Local Setup Required!

Unlike traditional setups, you don't need to:
- Install Python dependencies locally
- Set up PostgreSQL
- Manage virtual environments
- Install uv or other tools

Docker handles all of this automatically. Just run `docker-compose up` and you're ready to go!