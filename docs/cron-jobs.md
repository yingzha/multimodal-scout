# Cron Jobs & Monitoring

Multimodal Scout uses Docker-based cron jobs to automatically collect content from external sources. This document covers the automated content collection system and monitoring capabilities.

## Overview

The cron service runs in a separate Docker container and automatically:
- Runs the complete content processing pipeline every 2 hours
- Fetches content from all sources (Hacker News, Substack, Hugging Face) 
- Generates AI summaries for new content
- Creates embeddings for semantic search
- Applies filtering and content processing
- Saves everything to the database with optimized batch operations

## Schedule

| Job | Frequency | Schedule Expression | Description |
|-----|-----------|---------------------|-------------|
| Full Pipeline | Every 30 minutes | `*/30 * * * *` | Complete content processing: scraping + AI processing + database storage |

## Architecture

### Cron Service Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cron Daemon   │    │ Environment     │    │ Pipeline Runner │
│   (system)      │────│ Script          │────│                 │
│                 │    │ (cron_env.sh)   │    │ • run_pipeline.py│
│ • Schedule mgmt │    │ • DB connection │    │ • Full pipeline │
│ • Job execution │    │ • Path setup    │    │ • All scrapers  │
│ • Logging       │    │ • Env isolation │    │ • AI processing │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Environment Management

The cron jobs use a custom environment script (`cron_env.sh`) to ensure proper:
- Database connectivity (PostgreSQL service discovery)
- Python path configuration (uv package manager)
- Environment variable inheritance

## Monitoring & Logging

### Viewing Logs

Monitor cron job execution with Docker logs:

```bash
# View all cron logs
docker-compose logs cron

# Follow logs in real-time
docker-compose logs -f cron

# View recent logs (last 50 lines)
docker-compose logs cron --tail=50
```

### Log Format

Cron logs include:

**Job Start/End Markers:**
```
Mon Aug 19 16:00:00 UTC 2025: Starting full pipeline cron job
Mon Aug 19 16:00:45 UTC 2025: Full pipeline cron job completed
```

**Detailed Processing Logs:**
```
🤖 PIPELINE CRON JOB STARTED: 2025-08-19 16:00:00
🚀 Starting full content processing pipeline...
📋 STATUS: Scraping fresh content from Hugging Face and RSS sources...
📋 START: Starting unified processing pipeline...
📋 STATUS: Concurrent scraping complete: 50 HF papers, 60 RSS items
📋 STATUS: Saved 110 sources (60 new)
⏳ PROGRESS: 17% - Starting AI processing for 60 sources...
⏳ PROGRESS: 45% - Generating AI summaries...
📊 FINAL RESULTS: 100 items processed
📊 SOURCES: Research Papers, Industry News
✅ SUCCESS: Pipeline cron job completed successfully
⏱️  Total execution time: 45.23s
🏁 Job ended: 2025-08-19 16:00:45
```

### Performance Metrics

Each pipeline run logs:
- **Total execution time**: Complete pipeline duration (typically 30-90s depending on new content)
- **Progress tracking**: Real-time percentage completion through pipeline stages
- **Item counts**: Number of sources processed from each feed (HF papers, RSS items)
- **Processing breakdown**: Concurrent scraping, AI summary generation, database operations
- **Final results**: Total items available after filtering and processing

## Troubleshooting

### Common Issues

**1. Database Connection Errors**
```
sqlalchemy.exc.OperationalError: connection to server at "localhost" failed
```
- **Cause**: Environment variables not properly inherited by cron
- **Solution**: The `cron_env.sh` script handles this automatically
- **Check**: Verify cron service is using the environment script

**2. Missing Dependencies**
```
ModuleNotFoundError: No module named 'sqlalchemy'
```
- **Cause**: Python packages not available in cron environment
- **Solution**: Ensure cron jobs use `uv run` for dependency management
- **Check**: Verify Dockerfile.cron installs all dependencies

**3. API Rate Limiting**
```
Google API quota exceeded
```
- **Cause**: Too many requests to Google Gemini API
- **Solution**: Summary generation includes built-in caching
- **Check**: Monitor API usage in Google Cloud Console

### Manual Testing

Test the pipeline manually:

```bash
# Test full pipeline (recommended)
docker-compose exec cron /app/cron_env.sh /root/.local/bin/uv run python -m src.backend.run_pipeline

# Test individual scrapers (for debugging)
docker-compose exec cron /app/cron_env.sh /root/.local/bin/uv run python -m src.backend.run_scraper src.backend.scraper.scrape_rss_sources
docker-compose exec cron /app/cron_env.sh /root/.local/bin/uv run python -m src.backend.run_scraper src.backend.scraper.scrape_huggingface_trending_papers

# Test database connection
docker-compose exec cron /app/cron_env.sh /root/.local/bin/uv run python -c "from src.backend.database import db_manager; print('Database connected')"
```

### Service Management

```bash
# Restart cron service
docker-compose restart cron

# Rebuild cron service (after code changes)
docker-compose build cron && docker-compose up -d cron

# Check cron daemon status
docker-compose exec cron sh -c 'ls /proc/*/cmdline | xargs grep -l cron'
```

## Configuration

### Customizing Schedules

Edit `crontab` file to modify job schedules:

```bash
# Crontab format: minute hour day month weekday command
0 */2 * * *   # Every 2 hours at minute 0 (current pipeline)
0 * * * *     # Every hour at minute 0
0 */6 * * *   # Every 6 hours at minute 0  
0 0 * * *     # Daily at midnight
0 0 * * 0     # Weekly on Sunday at midnight
```

### Environment Variables

Required environment variables for cron jobs:

| Variable | Value | Purpose |
|----------|-------|---------|
| `DATABASE_URL` | `postgresql://scout_user:scout_password@postgres:5432/multimodal_scout` | Database connection |
| `GOOGLE_API_KEY` | Your API key | Google Gemini access |
| `PATH` | `/root/.local/bin:/usr/local/bin:/usr/bin:/bin` | Command search path |

## Security Considerations

- **Environment Isolation**: Each cron job runs with minimal environment
- **Database Access**: Uses service discovery (`postgres:5432`) instead of localhost
- **API Keys**: Stored in Docker environment variables, not in code
- **Logging**: Sensitive data is not logged (API keys, passwords)

## Performance Optimization

### Caching Strategy

- **Summary Cache**: Avoids regenerating summaries for known URLs using consolidated storage
- **Embedding Cache**: Reuses computed embeddings for semantic search with pre-generation
- **Batch Operations**: New `add_summaries_batch()` method reduces database round trips
- **Local Time Handling**: Timestamps use local time for accurate time-based filtering
- **Database Optimization**: Bulk operations and connection pooling

### Resource Management

- **Memory Usage**: Cron containers use minimal resources
- **CPU Usage**: AI processing runs efficiently with batching
- **Network**: Respects rate limits and uses connection pooling

## Maintenance

### Regular Tasks

1. **Log Rotation**: Monitor log file sizes
2. **Database Cleanup**: Periodic cleanup of old cache entries
3. **API Monitoring**: Track Google Gemini API usage
4. **Error Monitoring**: Review failed job logs

### Health Checks

The system includes automatic health monitoring:
- Database connectivity verification
- API endpoint availability checks
- Service dependency validation

## Future Improvements

- **Retry Logic**: Automatic retry for failed jobs
- **Alerting**: Notifications for persistent failures
- **Metrics**: Detailed performance tracking
- **Scaling**: Support for multiple cron instances