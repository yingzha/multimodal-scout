# Automated Content Pipeline

Multimodal Scout automatically discovers and processes content using a pipeline that runs every 30 minutes.

## How It Works

The automated pipeline:
- 🔍 **Discovers** content from Hacker News, Substack, Hugging Face, and Engineering Blogs
- 🤖 **Processes** with your local model for summaries and embeddings
- 🏷️ **Categorizes** content automatically
- 💾 **Stores** in PostgreSQL for search

It runs in the `pipeline` service of `docker/docker-compose.yml`, which loops `python -m src.backend.run_pipeline` and sleeps between runs. Runs never overlap.

## Running It

### Start with Automation
```bash
# Start all services (includes automated pipeline)
docker-compose -f docker/docker-compose.yml up -d

# Monitor pipeline execution
docker-compose -f docker/docker-compose.yml logs -f pipeline
```

### Manual Testing
```bash
# Trigger pipeline immediately
docker-compose -f docker/docker-compose.yml run --rm pipeline python -m src.backend.run_pipeline

# Check results
curl -X POST "http://localhost:8000/api/content/search" \
  -H "Content-Type: application/json" \
  -d '{"topics": ["AI"], "selectedDays": 1, "maxResults": 5}'
```

## Schedule & Performance

- **Frequency**: Every 30 minutes, measured from the end of the previous run (`PIPELINE_INTERVAL_SECONDS`, default 1800)
- **Duration**: Depends on your hardware and model. Summaries are generated at most `LLM_MAX_CONCURRENCY` at a time (default 2)
- **Sources**: Hacker News, Substack, Hugging Face Papers, Engineering Blogs
- **Model server down or model missing**: Each run first sends one small request to both models. If either fails, the run is skipped and retried at the next interval

## Monitoring

### View Logs
```bash
# Real-time pipeline logs
docker-compose -f docker/docker-compose.yml logs -f pipeline

# Recent logs
docker-compose -f docker/docker-compose.yml logs pipeline --tail=50

# All service status
docker-compose -f docker/docker-compose.yml ps
```

### Log Format
```
🤖 PIPELINE RUN STARTED: 2026-01-08 16:00:00
📋 STATUS: Scraping content from sources...
📋 STATUS: Found 110 items (60 new)
⏳ PROGRESS: 45% - Generating summaries...
📊 FINAL RESULTS: 100 items processed
✅ SUCCESS: Pipeline run completed successfully
```

## Troubleshooting

### Common Issues

**"LLM not ready, skipping this pipeline run"**
- Cause: Ollama (or the server at `LLM_BASE_URL`) is not running, is not reachable from the container, or does not have the models named in `LLM_CHAT_MODEL` and `LLM_EMBEDDING_MODEL`. The log line just above gives the reason
- Solution: Start it, pull the models, and check `docker-compose -f docker/docker-compose.yml exec backend curl -s http://host.docker.internal:11434/v1/models`. On Linux, Ollama must listen on an address the containers can reach (see the [Development Guide](development.md))

**Summaries fail or time out**
- Cause: The model is too slow for the timeout, or too many requests are in flight
- Solution: Raise `LLM_TIMEOUT_SECONDS`, lower `LLM_MAX_CONCURRENCY`, or use a smaller model

**Database Connection Errors**
- Cause: The `postgres` service is not healthy yet
- Solution: Check `docker-compose -f docker/docker-compose.yml ps` and restart the `pipeline` service

### Manual Testing
```bash
# Test database connection
docker-compose -f docker/docker-compose.yml exec backend python -c "from src.backend.database import db_manager; db_manager.create_tables(); print('Database connected')"

# Restart pipeline service
docker-compose -f docker/docker-compose.yml restart pipeline
```

## Configuration

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection |
| `LLM_BASE_URL` | OpenAI-compatible API of the model server |
| `LLM_CHAT_MODEL` | Model used for summaries |
| `LLM_EMBEDDING_MODEL` | Model used for search embeddings |
| `LLM_MAX_CONCURRENCY` | Summaries generated at the same time |
| `LLM_TIMEOUT_SECONDS` | Timeout for one model request |
| `PIPELINE_INTERVAL_SECONDS` | Pause between runs |

### Performance Optimizations

- **Caching**: Avoids regenerating summaries and embeddings for known content
- **Batch Operations**: Reduces database round trips
- **Concurrent Processing**: Parallel scraping, bounded parallel summarization
