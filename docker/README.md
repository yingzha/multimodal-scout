# Docker Configuration

This directory contains all Docker-related files for the Multimodal Scout project.

## Files

- `Dockerfile.backend` - Backend service (FastAPI + Python)
- `Dockerfile.frontend` - Frontend service (Next.js)
- `docker-compose.yml` - Local development environment
- `.dockerignore` - Files to exclude from Docker builds

## Usage

### Local Development

From the project root:

```bash
docker-compose -f docker/docker-compose.yml up
```

### Building Individual Images

```bash
# Backend
docker build -f docker/Dockerfile.backend -t multimodal-scout-backend .

# Frontend
docker build -f docker/Dockerfile.frontend -t multimodal-scout-frontend .
```
