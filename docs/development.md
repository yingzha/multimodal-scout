# Development Workflow Guide

This guide provides a streamlined workflow for developers actively working on the Multimodal Scout project. For initial setup, see the root [README.md](../README.md).

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

# Add a bookmark
curl -s -X POST "http://localhost:8000/api/bookmarks" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "link": "http://example.com", "source": "Test", "summary": "Test summary"}'

# Get specific bookmark (RESTful)
curl -s http://localhost:8000/api/bookmarks/BOOKMARK_ID

# Update bookmark summary (RESTful)
curl -s -X PATCH "http://localhost:8000/api/bookmarks/BOOKMARK_ID" \
  -H "Content-Type: application/json" \
  -d '{"summary": "Updated summary"}'

# Delete bookmark (RESTful)
curl -s -X DELETE "http://localhost:8000/api/bookmarks/BOOKMARK_ID"
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