# Multimodal Scout Backend

This backend service, built with Python and FastAPI, is the core of the Multimodal Scout application. It handles all content scraping, AI-powered processing, and data management with a RESTful API design.

## Backend-Specific Features

### Content Management
- **Multi-source scraping**: Fetches content from multiple RSS sources (Hacker News, Substack) and Hugging Face
- **AI-powered summarization**: Generates summaries using the Google Gemini API with intelligent caching
- **Smart content categorization**: Automatically categorizes content as Research, Industry, or General
- **Real-time progress**: Uses Server-Sent Events (SSE) to stream progress updates to the frontend

### API & Performance
- **RESTful API design**: Follows REST principles with proper resource naming and HTTP methods
- **Health monitoring**: Dedicated `/health` endpoint with database connectivity testing
- **Response caching**: Server-side caching (30-minute LRU cache) and client-side headers for improved performance
- **User-friendly error handling**: Structured error responses with helpful messages
- **Chrome bookmark export**: Generates Chrome-compatible bookmark files with folder organization

### Data Management
- **PostgreSQL database**: Robust data storage with UUID-based resource identification
- **Cache management**: CLI tools for database cleanup, search, and analytics
- **Automatic migrations**: Database schema management with Alembic
- **Bookmark management**: Full CRUD operations with both legacy and RESTful endpoints

## Development & Management Commands

All commands should be run from the project's root directory.

### Database Operations

```bash
# Connect directly to the PostgreSQL container
docker-compose exec postgres psql -U scout_user -d multimodal_scout

# Apply the latest database migrations
docker-compose exec backend alembic upgrade head

# Create a new, auto-generated migration file
docker-compose exec backend alembic revision --autogenerate -m "Your migration message"

# View migration history
docker-compose exec backend alembic history
```

### Cache Management CLI

The `cache_manager.py` script provides tools for inspecting and managing the database cache.

```bash
# View cache statistics (total items, age, etc.)
docker-compose exec backend python -m src.backend.cache_manager stats

# Search cached summaries by content
docker-compose exec backend python -m src.backend.cache_manager search --cache-type summary --query "AI" --limit 5

# Clean up old summaries (e.g., older than 30 days)
docker-compose exec backend python -m src.backend.cache_manager cleanup --cache-type summary --days 30
```

### General Development

```bash
# Run a one-off script (e.g., the scraper)
docker-compose exec backend python -m src.backend.scraper

# Access the backend container's shell for debugging
docker-compose exec backend bash

# View real-time logs for the backend service
docker-compose logs -f backend

# Restart the backend service
docker-compose restart backend
```

## Backend Architecture

### Core Components

- **`app.py`**: The main FastAPI application, serving API endpoints.
- **`pipeline.py`**: Contains the primary content processing logic, including smart filtering.
- **`scraper.py`**: Handles web scraping from multiple RSS sources and Hugging Face.
- **`search.py`**: Manages keyword and semantic searches, including embedding generation.
- **`database.py`**: Defines SQLAlchemy models for PostgreSQL tables (bookmarks, summaries, etc.).
- **`cache_manager.py`**: Implements the command-line interface for cache management.
- **`constants.py`**: Stores configuration values, such as semantic search thresholds.

### Data Flow

1.  **Scraping**: The cron job or a manual trigger runs the `scraper` to collect content.
2.  **Enrichment**: The `pipeline` generates AI summaries via Google Gemini for new content.
3.  **Caching**: All summaries and vector embeddings are stored in the PostgreSQL database to prevent reprocessing.
4.  **Filtering**: When a user requests content, the `pipeline` applies a multi-stage filter:
    1.  Keyword matches are prioritized.
    2.  Semantic search results are added based on relevance scores.
    3.  The final list is balanced according to the user's research/industry preference.
5.  **Delivery**: Results are streamed to the frontend via an SSE connection.

### Dependencies

Python dependencies are managed with `uv` and defined in `pyproject.toml`. Key dependencies include FastAPI, PostgreSQL drivers, Google Gemini client, and code quality tools (black, pylint). They are automatically installed within the Docker container, so no local installation is required.
