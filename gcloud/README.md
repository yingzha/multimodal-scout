# Google Cloud Configuration

This directory contains all Google Cloud deployment files for the Multimodal Scout project.

## Files

- `deploy-services.sh` - Main deployment script for Cloud Run services
- `setup-infrastructure.sh` - Initial infrastructure setup (databases, secrets, etc.)
- `cloudbuild.backend.yaml` - Cloud Build configuration for backend
- `cloudbuild.frontend.yaml` - Cloud Build configuration for frontend
- `cron_env.sh` - Environment setup for cron jobs
- `.env.cloud` - Cloud-specific environment variables

## Usage

### Initial Setup

```bash
cd gcloud
./setup-infrastructure.sh YOUR_PROJECT_ID us-central1
```

### Deployment

```bash
cd gcloud
./deploy-services.sh YOUR_PROJECT_ID us-central1
```

## Configuration

The deployment uses:
- Cloud Run for serverless container hosting
- Cloud SQL (PostgreSQL) for database
- Cloud Scheduler for periodic tasks
- Secret Manager for sensitive data
