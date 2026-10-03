# Docker Configuration

This directory contains all Docker-related files for the Multimodal Scout project.

## Files

- `Dockerfile.backend` - Backend service (FastAPI + Python)
- `Dockerfile.frontend` - Frontend service (Next.js)
- `docker-compose.yml` - Local environment: PostgreSQL, backend, pipeline loop, frontend

The `.dockerignore` for these builds lives in the project root.

## Usage

### Local Development

From the project root, with [Ollama](https://ollama.com) running on the host and `.env` created from `.env.example`:

```bash
docker-compose -f docker/docker-compose.yml up
```

The backend and frontend are published on `127.0.0.1` only. The containers reach the model server on the host through `host.docker.internal`.

### Building Individual Images

```bash
# Backend
docker build -f docker/Dockerfile.backend -t multimodal-scout-backend .

# Frontend
docker build -f docker/Dockerfile.frontend -t multimodal-scout-frontend .
```
