# Development Guide

Complete guide for developing Multimodal Scout. For quick setup, see the main [README.md](../README.md).

## 🚀 Initial Setup

### Prerequisites
- Docker and Docker Compose
- [Ollama](https://ollama.com) running on the host (see [Local Model Setup](#-local-model-setup))

### Quick Start
```bash
git clone https://github.com/yingzha/multimodal-scout.git
cd multimodal-scout

cp .env.example .env

# Pull the default models
ollama pull gemma3:4b
ollama pull bge-m3

# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Verify everything works
curl http://localhost:8000/health
curl http://localhost:3000
```

The backend and frontend are published on `127.0.0.1` only, and PostgreSQL is reachable only from the other containers. The app does not authenticate requests, so add your own authentication before exposing it beyond your machine.

## 🤖 Local Model Setup

The backend talks to any OpenAI-compatible API. The defaults target Ollama running natively on the host, which lets it use the GPU (Docker on macOS cannot).

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_BASE_URL` | `http://localhost:11434/v1` (`http://host.docker.internal:11434/v1` in `.env.example`) | Base URL of the API. Set it to empty to turn AI features off |
| `LLM_API_KEY` | `ollama` | API key sent as a bearer token |
| `LLM_CHAT_MODEL` | `gemma3:4b` | Summaries, categorization, keyword suggestions |
| `LLM_EMBEDDING_MODEL` | `bge-m3` | Semantic search embeddings |
| `LLM_TIMEOUT_SECONDS` | `120` | Timeout for one request |
| `LLM_MAX_CONCURRENCY` | `2` | Summaries generated at the same time |

```bash
# Check that the containers can reach the model server
docker-compose -f docker/docker-compose.yml exec backend curl -s http://host.docker.internal:11434/v1/models
```

**Linux**: Ollama listens on `127.0.0.1` by default, which containers cannot reach. Make it listen on the Docker bridge address (for example `OLLAMA_HOST=172.17.0.1` in the Ollama service environment) and keep `LLM_BASE_URL` pointing at `host.docker.internal`.

**Other servers**: For LM Studio, llama.cpp, vLLM or a hosted provider, set `LLM_BASE_URL`, `LLM_API_KEY` and the two model names to match. The server must offer both `/chat/completions` and `/embeddings`.

### Search Thresholds

Semantic search keeps a source when its cosine similarity to a topic is above `RESEARCH_THRESHOLD` or `INDUSTRY_THRESHOLD` (both default to `0.52`, measured for `bge-m3`). Similarity scores are specific to the embedding model, so re-measure the thresholds after changing `LLM_EMBEDDING_MODEL`:

```bash
# Print the score distribution of recent sources against the default topics,
# and the titles ranked around the current thresholds
docker-compose -f docker/docker-compose.yml exec backend python -m src.backend.cache_manager calibrate --days 7
```

Pick the cutoffs where the titles stop being on topic and set them in `.env`. With `bge-m3`, scores sit in a narrow band (on-topic items around 0.52 to 0.65), so small changes move a lot of results.

### Changing the Embedding Model

Cached embeddings are tied to the model that produced them. After changing `LLM_EMBEDDING_MODEL`, old vectors are ignored and replaced as texts are embedded again. To do that up front instead of during the first search:

```bash
docker-compose -f docker/docker-compose.yml exec backend python -m src.backend.cache_manager reembed --days 7
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
docker-compose -f docker/docker-compose.yml logs -f pipeline

# Manual pipeline trigger
docker-compose -f docker/docker-compose.yml run --rm pipeline python -m src.backend.run_pipeline
```

## Making Changes

The project is configured for hot reloading. When you save changes to a file, the relevant service will automatically update.

-   **Backend Changes**: Edit files in the `src/backend/` directory.
-   **Frontend Changes**: Edit files in the `src/frontend/` directory.
-   **Database Schema Changes**: See the [Database Migrations](#-database-migrations) section below for detailed workflows.

## Testing

### Backend Unit Tests

Run the backend test suite using `pytest`. The database tests insert and clean up rows, so run them against a scratch database, never the one holding your bookmarks:

```bash
# One-time: create the scratch database
docker-compose -f docker/docker-compose.yml exec postgres createdb -U scout_user multimodal_scout_test

# Run the tests in the running backend container (dev dependencies live in the `dev` extra)
TEST_DB=postgresql://scout_user:scout_password@postgres:5432/multimodal_scout_test
docker-compose -f docker/docker-compose.yml exec --user root -e DATABASE_URL=$TEST_DB backend python -m src.backend.cache_manager init
docker-compose -f docker/docker-compose.yml exec --user root -e DATABASE_URL=$TEST_DB backend uv run --extra dev pytest tests/backend/
```

The tests mock the model server, so Ollama does not need to be running.

### Frontend Checks

Type-check and lint the frontend:
```bash
docker-compose -f docker/docker-compose.yml exec frontend npx tsc --noEmit
docker-compose -f docker/docker-compose.yml exec frontend npm run lint
```

### Integration Tests (API)

Test the running API endpoints with `curl`.

```bash
# Health & content
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/topics
curl -s -X POST "http://localhost:8000/api/content/search" \
  -H "Content-Type: application/json" \
  -d '{"selectedDays": 1, "topics": ["ai"], "maxResults": 10, "researchRatio": 0.5}'

# Preferences and bookmarks (everything belongs to the local user)
curl -s http://localhost:8000/api/user/preferences
curl -s http://localhost:8000/api/bookmarks
curl -s -X POST "http://localhost:8000/api/bookmarks" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "link": "http://example.com", "source": "Test", "summary": "Test summary"}'
curl -s -X DELETE "http://localhost:8000/api/bookmarks/BOOKMARK_ID"
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
    The frontend keeps `node_modules` in an anonymous volume that survives a rebuild, so after changing `package.json` also renew that volume:
    ```bash
    docker-compose -f docker/docker-compose.yml up -d --build --renew-anon-volumes frontend
    ```

## Code Quality Tools

The backend includes code quality and formatting tools:

> Dev tooling lives in the optional `dev` extra. Include `--extra dev` the first time so the formatter/linter are available in the container.

```bash
# Format Python code with black
docker-compose -f docker/docker-compose.yml exec --user root backend uv run --extra dev black src/backend/

# Run pylint for code quality analysis
docker-compose -f docker/docker-compose.yml exec --user root backend uv run --extra dev pylint src/backend/

# Install/sync new dependencies (includes dev tools)
docker-compose -f docker/docker-compose.yml exec --user root backend uv sync --extra dev
```

## 🗄️ Database Migrations

On startup the backend creates any missing tables from the models in `src/backend/database.py`. It does not run Alembic, and it does not alter tables that already exist. When you change the structure of an existing database (add columns, etc.), create and apply a migration.

### 📝 Creating Migrations

A database created by the backend has no Alembic version recorded, and `alembic upgrade head` fails on it because the tables already exist. Record it as up to date once, before your first migration:

```bash
docker-compose -f docker/docker-compose.yml exec backend alembic stamp head
```

Then, for each schema change:

1. **Modify your models** in `src/backend/database.py`
2. **Generate migration**:
   ```bash
   docker-compose -f docker/docker-compose.yml exec backend alembic revision --autogenerate -m "Add new feature"
   ```
3. **Apply locally**:
   ```bash
   docker-compose -f docker/docker-compose.yml exec backend alembic upgrade head
   ```

### 🔍 Checking Migration Status

```bash
# See current migration version
docker-compose -f docker/docker-compose.yml exec backend alembic current

# View all migrations
docker-compose -f docker/docker-compose.yml exec backend alembic history
```

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

# Clear all content (keep bookmarks)
DELETE FROM sources;
DELETE FROM seen_cards;
DELETE FROM embedding_cache;

# Clear bookmarks and the local user (restart the backend afterwards to recreate the user)
DELETE FROM bookmarks;
DELETE FROM users;

# Check table sizes
SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;
```
