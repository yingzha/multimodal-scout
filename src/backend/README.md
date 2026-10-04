# Backend Service

FastAPI-based backend service for Multimodal Scout. Handles content discovery, AI processing, and bookmark storage.

> For complete setup and usage instructions, see [docs/development.md](../../docs/development.md)  
> For API documentation, see [docs/api.md](../../docs/api.md)  
> For automated pipeline details, see [docs/pipeline.md](../../docs/pipeline.md)

## 🚀 Key Features

- 🤖 **AI-Powered Processing**: Summaries and embeddings from a local model through any OpenAI-compatible API (Ollama by default)
- 📡 **Multi-Source Scraping**: Hacker News, Substack, Hugging Face, and Engineering Blogs content
- 📚 **Bookmarks**: Bookmark and preference storage for a single local user
- 📊 **Real-time Updates**: Server-Sent Events for live progress tracking
- 🗄️ **PostgreSQL Integration**: Robust data storage with Alembic migrations

## 🛠️ Backend-Specific Commands

### Database Management
```bash
# Database console
docker-compose -f docker/docker-compose.yml exec postgres psql -U scout_user -d multimodal_scout

# Migrations (run `alembic stamp head` once on a database created by the backend)
docker-compose -f docker/docker-compose.yml exec backend alembic upgrade head
docker-compose -f docker/docker-compose.yml exec backend alembic revision --autogenerate -m "Description"
```

### Cache Management
```bash
# Statistics
docker-compose -f docker/docker-compose.yml exec backend python -m src.backend.cache_manager stats

# Cleanup
docker-compose -f docker/docker-compose.yml exec backend python -m src.backend.cache_manager cleanup --cache-type summary --days 30

# Re-embed recent summaries after changing the embedding model
docker-compose -f docker/docker-compose.yml exec backend python -m src.backend.cache_manager reembed --days 7

# Print similarity scores to choose search thresholds
docker-compose -f docker/docker-compose.yml exec backend python -m src.backend.cache_manager calibrate --days 7
```

### Service Control
```bash
# View logs
docker-compose -f docker/docker-compose.yml logs -f backend

# Restart service
docker-compose -f docker/docker-compose.yml restart backend

# Shell access
docker-compose -f docker/docker-compose.yml exec backend bash
```

## 🏗️ Architecture

**Core Components:**
- `app.py` - FastAPI application with API endpoints
- `pipeline.py` - Content processing and AI integration  
- `client.py` - LLM client for the OpenAI-compatible API
- `scraper.py` - Multi-source content discovery
- `database.py` - SQLAlchemy models and storage
- `cache_manager.py` - CLI tools for data management

**Processing Flow:**
1. **Discover** content from multiple sources (scheduled/manual)
2. **Process** with AI summarization (local model)
3. **Store** with semantic embeddings (PostgreSQL) 
4. **Filter** and rank based on user preferences
5. **Deliver** via real-time API responses

For detailed development workflows, see the main [Development Guide](../../docs/development.md).
