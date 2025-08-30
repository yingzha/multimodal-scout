# Automated Content Pipeline

Multimodal Scout automatically discovers and processes content using an intelligent pipeline that runs every 30 minutes.

## How It Works

The automated pipeline:
- 🔍 **Discovers** content from Hacker News, Substack, and Hugging Face
- 🤖 **Processes** with Google Gemini AI for summaries  
- 🏷️ **Categorizes** content automatically
- 💾 **Stores** in PostgreSQL for search

## Local Development

### Start with Automation
```bash
# Start all services (includes automated pipeline)
docker-compose up -d

# Monitor pipeline execution
docker-compose logs -f cron
```

### Manual Testing
```bash
# Trigger pipeline immediately
curl -X POST "http://localhost:8000/pipeline" \
  -H "Authorization: Bearer test-token"

# Check results
curl -X POST "http://localhost:8000/api/content/search" \
  -H "Content-Type: application/json" \
  -d '{"topics": ["AI"], "selectedDays": 1, "maxResults": 5}'
```

## Cloud Deployment

In production, the pipeline runs via Google Cloud Scheduler:

```bash
# Deploy with automated pipeline
./scripts/configure-env.sh cloud
./deploy-services.sh YOUR_PROJECT_ID us-central1
```

**Cloud Features:**
- ⏰ Runs every 30 minutes via Cloud Scheduler  
- 📊 Built-in logging and monitoring
- 🔒 OIDC authentication for security
- 💰 Scales to zero when not processing

## Schedule & Performance

- **Frequency**: Every 30 minutes (`*/30 * * * *`)
- **Duration**: 30-90 seconds per run
- **Sources**: Hacker News, Substack, Hugging Face Papers
- **Processing**: ~50-100 items per run

## Monitoring

### View Logs
```bash
# Real-time pipeline logs
docker-compose logs -f cron

# Recent logs
docker-compose logs cron --tail=50

# All service status
docker-compose ps
```

### Log Format
```
🤖 PIPELINE STARTED: 2024-08-19 16:00:00
📋 STATUS: Scraping content from sources...
📋 STATUS: Found 110 items (60 new)
⏳ PROGRESS: 45% - Generating summaries...
📊 RESULTS: 100 items processed
✅ SUCCESS: Pipeline completed in 45.23s
```

## Troubleshooting

### Common Issues

**Database Connection Errors**
- Cause: Environment variables not inherited
- Solution: Handled automatically by `cron_env.sh` script

**Missing Dependencies** 
- Cause: Python packages not available
- Solution: Ensure cron uses `uv run` for execution

**API Rate Limiting**
- Cause: Too many Google Gemini requests
- Solution: Built-in caching prevents repeated requests

### Manual Testing
```bash
# Test full pipeline
docker-compose exec cron /app/cron_env.sh /root/.local/bin/uv run python -m src.backend.run_pipeline

# Test database connection
docker-compose exec cron /app/cron_env.sh /root/.local/bin/uv run python -c "from src.backend.database import db_manager; print('Database connected')"

# Restart cron service
docker-compose restart cron
```

## Configuration

### Required Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection |
| `GOOGLE_API_KEY` | Google Gemini access |

### Performance Optimizations

- **Caching**: Avoids regenerating summaries for known URLs
- **Batch Operations**: Reduces database round trips  
- **Concurrent Processing**: Parallel scraping and AI processing
- **Resource Limits**: Minimal container resource usage

## Security

- Environment isolation for each cron job
- Service discovery instead of localhost connections
- API keys stored in environment variables
- No sensitive data in logs