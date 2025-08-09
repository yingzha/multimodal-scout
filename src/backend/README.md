# Multimodal Scout Backend

A Python-based content scouting system that scrapes, summarizes, and filters sources from Hacker News and Hugging Face using AI-powered summarization and semantic search.

## Features

- **Multi-source scraping**: Hacker News stories and Hugging Face trending papers
- **AI-powered summarization**: Generates summaries using Google Gemini API
- **Smart Balanced Filtering**: Advanced filtering with separate semantic thresholds for research (0.65) vs industry (0.55) content
- **Configurable results**: User-adjustable result limits (5-50) and research/industry balance ratios
- **Intelligent search**: Keyword search prioritized first, then semantic search by relevance score
- **Comprehensive caching**: PostgreSQL database for summaries and embeddings with persistent storage
- **Real-time progress**: Server-Sent Events (SSE) for streaming progress updates
- **Cache management**: Built-in CLI tools for cleanup, search, and analytics

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

- **`merger.py`**: Main pipeline orchestration with advanced filtering logic
- **`scraper.py`**: Web scraping for sources (Hugging Face, Hacker News)
- **`search.py`**: Keyword and semantic search with embedding generation and caching
- **`app.py`**: FastAPI server with streaming endpoints and Smart Balanced Search
- **`database.py`**: SQLAlchemy models for PostgreSQL (summaries, embeddings, bookmarks)
- **`db_cache.py`**: Database operations for summary and embedding caching
- **`cache_manager.py`**: CLI cache management tool with statistics and cleanup
- **`constants.py`**: Configuration including semantic search thresholds

### Data Flow

1. **Scraping**: Collect sources from Hugging Face and Hacker News
2. **Enrichment**: Generate AI summaries using Google Gemini (cached in PostgreSQL)
3. **Advanced Filtering**: 
   - Priority 1: Keyword search results (research first, then industry)
   - Priority 2: Semantic search with separate thresholds (research: 0.65, industry: 0.55)
   - Smart balancing: Configurable research/industry ratios with overflow handling
4. **Embedding Caching**: Store Google Gemini embeddings to optimize future searches
5. **Result Delivery**: Return balanced, ordered results with real-time progress updates
6. **Management**: CLI tools for cache cleanup, statistics, and content search

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