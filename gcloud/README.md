# Google Cloud Configuration

This directory contains all Google Cloud deployment files for the Multimodal Scout project.

## Files

- `setup-infrastructure.sh` - Initial infrastructure setup (APIs, secrets, service accounts)
- `setup-db-instance.sh` - Database VM provisioning (PostgreSQL 18 on Compute Engine e2-micro)
- `pg-startup.sh` - PostgreSQL startup script used by the VM
- `deploy-services.sh` - Main deployment script for Cloud Run services
- `cloudbuild.backend.yaml` - Cloud Build configuration for backend
- `cloudbuild.frontend.yaml` - Cloud Build configuration for frontend

**Note:** Secrets (API keys, database password) are stored in Google Secret Manager. Local dev uses `.env` in the project root.

## Usage

### Initial Setup

```bash
./gcloud/setup-infrastructure.sh YOUR_PROJECT_ID us-central1
./gcloud/setup-db-instance.sh YOUR_PROJECT_ID us-central1-a
```

### Deployment

```bash
./gcloud/deploy-services.sh YOUR_PROJECT_ID us-central1
```

## Configuration

The deployment uses:
- Cloud Run for serverless container hosting
- Compute Engine e2-micro (free tier) for self-managed PostgreSQL 18
- Cloud Scheduler for periodic tasks
- Secret Manager for sensitive data
