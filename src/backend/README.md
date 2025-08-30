# Backend Service

FastAPI-based backend service for Multimodal Scout. Handles content discovery, AI processing, and user management.

## 🚀 Key Features

- 🤖 **AI-Powered Processing**: Google Gemini integration for content summarization
- 📡 **Multi-Source Scraping**: Hacker News, Substack, and Hugging Face content
- 🔒 **Secure Authentication**: User registration, sessions, and bookmark management  
- 📊 **Real-time Updates**: Server-Sent Events for live progress tracking
- 🗄️ **PostgreSQL Integration**: Robust data storage with automated migrations

## 🛠️ Development Commands

### Database Management
```bash
# Database console
docker-compose exec postgres psql -U scout_user -d multimodal_scout

# Migrations
docker-compose exec backend alembic upgrade head
docker-compose exec backend alembic revision --autogenerate -m "Description"
```

### Cache Management
```bash
# Statistics
docker-compose exec backend python -m src.backend.cache_manager stats

# Cleanup
docker-compose exec backend python -m src.backend.cache_manager cleanup --cache-type summary --days 30
```

### Service Control
```bash
# View logs
docker-compose logs -f backend

# Restart service
docker-compose restart backend

# Shell access
docker-compose exec backend bash
```

## 🏗️ Architecture

**Core Components:**
- `app.py` - FastAPI application with API endpoints
- `pipeline.py` - Content processing and AI integration  
- `scraper.py` - Multi-source content discovery
- `database.py` - SQLAlchemy models and storage
- `cache_manager.py` - CLI tools for data management

**Processing Flow:**
1. **Discover** content from multiple sources (cron/manual)
2. **Process** with AI summarization (Google Gemini)
3. **Store** with semantic embeddings (PostgreSQL) 
4. **Filter** and rank based on user preferences
5. **Deliver** via real-time API responses

For detailed development workflows, see the main [Development Guide](../../docs/development.md).
