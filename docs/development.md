# Development Guide

Complete guide for developing Multimodal Scout. For quick setup, see the main [README.md](../README.md).

## 🚀 Initial Setup

### Prerequisites
- Docker and Docker Compose
- [Google Gemini API key](https://aistudio.google.com/app/apikey)

### Quick Start
```bash
git clone https://github.com/yingzha/multimodal-scout.git
cd multimodal-scout

# Configure environment
./scripts/configure-env.sh local

# Update your Google API Key

# Start all services
docker-compose up -d

# Verify everything works
curl http://localhost:8000/health
curl http://localhost:3000
```

## 🛠️ Common Commands

### Service Management  
```bash
# Start all services
docker-compose up -d

# View service status
docker-compose ps

# View logs
docker-compose logs -f [service]     # Specific service
docker-compose logs -f               # All services

# Stop services
docker-compose down

# Rebuild after dependency changes
docker-compose up -d --build [service]
```

### Pipeline Control
```bash
# Watch automated pipeline (every 30 min)
docker-compose logs -f cron

# Manual pipeline trigger
curl -X POST localhost:8000/pipeline \
  -H "Authorization: Bearer test-token"

# Check pipeline status
curl localhost:8000/health
```

## Making Changes

The project is configured for hot reloading. When you save changes to a file, the relevant service will automatically update.

-   **Backend Changes**: Edit files in the `src/backend/` directory.
-   **Frontend Changes**: Edit files in the `src/frontend/` directory.
-   **Database Schema Changes**: See the [Database Migrations](#-database-migrations) section below for detailed workflows.

## Testing

### Backend Unit Tests

Run the backend test suite using `pytest`:

```bash
docker-compose run --rm backend pytest tests/backend/
```

### Frontend Checks

Verify TypeScript compilation and basic functionality.
```bash
docker-compose exec frontend timeout 10s npm run dev || echo "✅ Frontend TypeScript compilation passed"
```
> **Note**: The frontend uses Next.js App Router which provides integrated TypeScript checking. The `timeout` command stops the dev server after compilation succeeds, avoiding the need for a full production build during testing.

### Integration Tests (API)

You can use `curl` to test the running API endpoints directly.

```bash
# Check health
curl -s http://localhost:8000/health

# Fetch topics  
curl -s http://localhost:8000/api/topics

# Search content (RESTful endpoint)
curl -s -X POST "http://localhost:8000/api/content/search" \
  -H "Content-Type: application/json" \
  -d '{"selectedDays": 1, "topics": ["ai"], "maxResults": 10, "researchRatio": 0.5}'

# --- Auth Endpoints ---
# Register a new user
curl -s -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123", "username": "testuser"}'

# Login and get a session token (requires jq to be installed)
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}' | jq -r .session_token)

echo "Got token: $TOKEN"

# Get current user info
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/auth/me

# --- Authenticated Bookmark Endpoints ---
# Add a bookmark
curl -s -X POST "http://localhost:8000/api/bookmarks" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title": "Test", "link": "http://example.com", "source": "Test", "summary": "Test summary"}'

# Get all bookmarks for the user
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/bookmarks

# Get specific bookmark (replace BOOKMARK_ID with a real ID)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/bookmarks/BOOKMARK_ID

# Update bookmark summary (replace BOOKMARK_ID with a real ID)
curl -s -X PATCH "http://localhost:8000/api/bookmarks/BOOKMARK_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"summary": "Updated summary"}'

# Delete bookmark (replace BOOKMARK_ID with a real ID)
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/bookmarks/BOOKMARK_ID"

# Logout
curl -s -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/auth/logout
```

## Common Docker Commands

-   **View Logs in Real-Time**:
    ```bash
    # Follow logs for all services
    docker-compose logs -f

    # Follow logs for a specific service (e.g., backend)
    docker-compose logs -f backend
    ```

-   **Access the Database**:
    ```bash
    docker-compose exec postgres psql -U scout_user -d multimodal_scout
    ```

-   **Rebuild a Service**:
    If you change dependencies (e.g., in `pyproject.toml` or `package.json`), you will need to rebuild the service's image.
    ```bash
    docker-compose up -d --build <service_name>
    # e.g., docker-compose up -d --build backend
    ```

## Code Quality Tools

The backend includes code quality and formatting tools:

```bash
# Format Python code with black
docker-compose exec backend uv run black src/backend/

# Run pylint for code quality analysis
docker-compose exec backend uv run pylint src/backend/

# Install/sync new dependencies
docker-compose exec backend uv sync
```

## 🗄️ Database Migrations

When you change the database structure (add columns, tables, etc.), you need to create and apply migrations.

### 📝 Creating Migrations (Local Development)

1. **Modify your models** in `src/backend/database.py`
2. **Generate migration**:
   ```bash
   docker-compose exec backend alembic revision --autogenerate -m "Add new feature"
   ```
3. **Apply locally**:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

### 🚀 Deploying Migrations to Cloud

**Good news**: Migrations run automatically when you deploy!

```bash
# Just deploy as normal - migrations happen automatically
./deploy-services.sh YOUR_PROJECT_ID us-central1
```

The backend will:
- ✅ Check database connection
- ✅ Run pending migrations automatically  
- ✅ Start the service

### 🔧 Manual Migration (If Automatic Fails)

If you see migration errors in the logs, run this complete command:

```bash
# 1. Install Cloud SQL Proxy (one-time setup)
gcloud components install cloud_sql_proxy

# 2. Get database password
DB_PASSWORD=$(gcloud secrets versions access latest --secret="database-password")

# 3. Start proxy and run SQL directly
cloud_sql_proxy -instances YOUR_PROJECT_ID:us-central1:multimodal-scout-db=tcp:9470

# 4. Execute your migration SQL (example)
PGPASSWORD="$DB_PASSWORD" psql -h 127.0.0.1 -p 9470 -U scout_user -d multimodal_scout -c "
ALTER TABLE users ADD COLUMN IF NOT EXISTS custom_topics JSON DEFAULT '[]'::json;
UPDATE users SET custom_topics = '[]'::json WHERE custom_topics IS NULL;
"

# 5. Stop proxy
pkill cloud_sql_proxy
```

### 🔍 Checking Migration Status

```bash
# See current migration version
docker-compose exec backend alembic current

# View all migrations
docker-compose exec backend alembic history
```

**That's it!** Most of the time, migrations just work automatically when you deploy. 🎉
