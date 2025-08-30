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
echo "GOOGLE_API_KEY=your_actual_api_key" >> .env

# Start all services
docker-compose up -d

# Verify everything works
curl http://localhost:8000/health
curl http://localhost:3000
```

## 🛠️ Common Commands

### Environment Management
```bash
# Switch to local development
./scripts/configure-env.sh local

# Switch to cloud deployment  
./scripts/configure-env.sh cloud
```

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
-   **Database Schema Changes**:
    1.  Modify the SQLAlchemy models in `src/backend/database.py`.
    2.  Generate a new migration script:
        ```bash
        docker-compose exec backend alembic revision --autogenerate -m "Your migration message"
        ```
    3.  Apply the migration to the database:
        ```bash
        docker-compose exec backend alembic upgrade head
        ```

## Testing

### Backend Unit Tests

Run the backend test suite using `pytest`:

```bash
docker-compose run --rm backend pytest tests/backend/
```

### Frontend Checks

-   **Type Checking**: Run the TypeScript compiler to check for type errors.
    ```bash
    docker-compose exec frontend npx tsc --noEmit
    ```
-   **Build Test**: Create a production build to ensure it compiles correctly.
    ```bash
    docker-compose exec frontend npm run build
    ```

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

# Create content from URL
curl -s -X POST "http://localhost:8000/api/content" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

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