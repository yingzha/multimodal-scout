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

# Add your Gemini API key and Firebase config to .env

# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Verify everything works
curl http://localhost:8000/health
curl http://localhost:3000
```

## 🛠️ Common Commands

### Service Management  
```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# View service status
docker-compose -f docker/docker-compose.yml ps

# View logs
docker-compose -f docker/docker-compose.yml logs -f [service]     # Specific service
docker-compose -f docker/docker-compose.yml logs -f               # All services

# Stop services
docker-compose -f docker/docker-compose.yml down

# Rebuild after dependency changes
docker-compose -f docker/docker-compose.yml up -d --build [service]
```

### Pipeline Control
```bash
# Watch automated pipeline (every 30 min)
docker-compose -f docker/docker-compose.yml logs -f cron

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

Run the backend test suite using `pytest`. The testing dependencies live in the `dev` extra, so include it when invoking `uv`:

```bash
docker-compose -f docker/docker-compose.yml run --rm backend uv run --extra dev pytest tests/backend/
```

> Tip: if you plan to run tests repeatedly in the same container, sync the dev extra once first (`docker-compose -f docker/docker-compose.yml exec backend uv sync --extra dev`) and then use `uv run pytest …` without the extra flag on subsequent runs.

### Frontend Checks

Verify TypeScript compilation and basic functionality.
```bash
docker-compose -f docker/docker-compose.yml exec frontend timeout 10s npm run dev || echo "✅ Frontend TypeScript compilation passed"
```
> **Note**: The frontend uses Next.js App Router which provides integrated TypeScript checking. The `timeout` command stops the dev server after compilation succeeds, avoiding the need for a full production build during testing.

### Integration Tests (API)

Test the running API endpoints with `curl`.

```bash
# Health & content
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/topics
curl -s -X POST "http://localhost:8000/api/content/search" \
  -H "Content-Type: application/json" \
  -d '{"selectedDays": 1, "topics": ["ai"], "maxResults": 10, "researchRatio": 0.5}'

# Auth (sign in via browser, then use session token from response)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/auth/me

# Bookmarks (requires auth)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/bookmarks
curl -s -X POST "http://localhost:8000/api/bookmarks" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title": "Test", "link": "http://example.com", "source": "Test", "summary": "Test summary"}'
curl -s -X DELETE -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/bookmarks/BOOKMARK_ID"
curl -s -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/auth/logout
```

## Common Docker Commands

-   **View Logs in Real-Time**:
    ```bash
    # Follow logs for all services
    docker-compose -f docker/docker-compose.yml logs -f

    # Follow logs for a specific service (e.g., backend)
    docker-compose -f docker/docker-compose.yml logs -f backend
    ```

-   **Access the Database**:
    ```bash
    docker-compose -f docker/docker-compose.yml exec postgres psql -U scout_user -d multimodal_scout
    ```

-   **Rebuild a Service**:
    If you change dependencies (e.g., in `pyproject.toml` or `package.json`), you will need to rebuild the service's image.
    ```bash
    docker-compose -f docker/docker-compose.yml up -d --build <service_name>
    # e.g., docker-compose -f docker/docker-compose.yml up -d --build backend
    ```

## Code Quality Tools

The backend includes code quality and formatting tools:

> Dev tooling lives in the optional `dev` extra. Include `--extra dev` the first time so the formatter/linter are available in the container.

```bash
# Format Python code with black
docker-compose -f docker/docker-compose.yml exec backend uv run --extra dev black src/backend/

# Run pylint for code quality analysis
docker-compose -f docker/docker-compose.yml exec backend uv run --extra dev pylint src/backend/

# Install/sync new dependencies (includes dev tools)
docker-compose -f docker/docker-compose.yml exec backend uv sync --extra dev
```

## 🗄️ Database Migrations

When you change the database structure (add columns, tables, etc.), you need to create and apply migrations.

### 📝 Creating Migrations (Local Development)

1. **Modify your models** in `src/backend/database.py`
2. **Generate migration**:
   ```bash
   docker-compose -f docker/docker-compose.yml exec backend alembic revision --autogenerate -m "Add new feature"
   ```
3. **Apply locally**:
   ```bash
   docker-compose -f docker/docker-compose.yml exec backend alembic upgrade head
   ```

### 🚀 Deploying Migrations to Cloud

**Good news**: Migrations run automatically when you deploy!

```bash
# Just deploy as normal - migrations happen automatically
gcloud/deploy-services.sh YOUR_PROJECT_ID us-central1
```

The backend will:
- ✅ Check database connection
- ✅ Run pending migrations automatically  
- ✅ Start the service

### 🔧 Manual Migration (If Automatic Fails)

If you see migration errors in the logs, run this complete command:

```bash
# 1. SSH tunnel to the database VM (keep this terminal open)
gcloud compute ssh multimodal-scout-db --zone=us-central1-a -- -L 5433:localhost:5432

# 2. In another terminal, get database password and run SQL
DB_PASSWORD=$(gcloud secrets versions access latest --secret="database-password")
PGPASSWORD="$DB_PASSWORD" psql -h 127.0.0.1 -p 5433 -U scout_user -d multimodal_scout

# Or run Alembic migrations directly
DATABASE_URL="postgresql://scout_user:$DB_PASSWORD@127.0.0.1:5433/multimodal_scout" alembic upgrade head
```

### 🔍 Checking Migration Status

```bash
# See current migration version
docker-compose -f docker/docker-compose.yml exec backend alembic current

# View all migrations
docker-compose -f docker/docker-compose.yml exec backend alembic history
```

**That's it!** Most of the time, migrations just work automatically when you deploy. 🎉

## 🧹 Database Cleanup

### Reset Database (Nuclear Option)
```bash
# Stop services, delete volumes, restart fresh
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d
```

### Selective Cleanup
```bash
# Access database shell
docker compose -f docker/docker-compose.yml exec postgres psql -U scout_user -d multimodal_scout

# Clear all content (keep users)
DELETE FROM summaries;
DELETE FROM seen_cards;

# Clear all users and their data
DELETE FROM bookmarks;
DELETE FROM users;

# Check table sizes
SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;
```

### Cloud Database Cleanup
```bash
# SSH tunnel to the database VM (keep this terminal open)
gcloud compute ssh multimodal-scout-db --zone=us-central1-a -- -L 5433:localhost:5432

# In another terminal, connect with psql
DB_PASSWORD=$(gcloud secrets versions access latest --secret="database-password")
PGPASSWORD="$DB_PASSWORD" psql -h 127.0.0.1 -p 5433 -U scout_user -d multimodal_scout
```
