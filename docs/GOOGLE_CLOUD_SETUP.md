# Google Cloud Migration Guide

## Cost-Optimized Setup for Low Traffic (<10 DAU)

**Total Estimated Cost: $10-20/month**

### Prerequisites

1. Google Cloud account with billing enabled
2. `gcloud` CLI installed and authenticated
3. Docker installed locally
4. Google API key (Gemini) stored in Secret Manager
5. Firebase project configured with Google Sign-In enabled
6. Firebase API key stored in Secret Manager (`firebase-api-key`)

### Quick Start

1. **Clone and prepare project:**
```bash
cd multimodal-scout
export GOOGLE_API_KEY="your-gemini-api-key-here"
```

2. **Run the complete setup:**
```bash
# Replace with your actual project ID
./gcloud/setup-infrastructure.sh your-project-id us-central1
./gcloud/setup-db-instance.sh your-project-id us-central1-a
./gcloud/deploy-services.sh your-project-id us-central1
```

3. **That's it!** Your app will be running on Google Cloud.

### Architecture Overview

- **Frontend**: Cloud Run (Next.js) - Auto-scales to 0, FREE for <10 DAU
- **Backend**: Cloud Run (FastAPI) - Auto-scales to 0, FREE for <10 DAU
- **Database**: Compute Engine e2-micro (PostgreSQL 18) - Free tier
- **Cron Jobs**: Cloud Scheduler + Cloud Run Jobs - FREE for low frequency
- **Secrets**: Secret Manager - 6 secrets FREE
- **Images**: Artifact Registry - FREE tier


### Services Created

**Cloud Run Services:**
- `multimodal-scout-backend` - FastAPI API server
- `multimodal-scout-frontend` - Next.js web app
- **Pipeline**: Cloud Scheduler calls `POST /pipeline` every 30 minutes (no separate cron service)

**Compute Engine:**
- Instance: `multimodal-scout-db` (e2-micro, PostgreSQL 18)
- Database: `multimodal_scout`
- User: `scout_user`

**Scheduled Jobs:**
- Pipeline: Every 30 minutes via Cloud Scheduler

### Configuration Files

- `gcloud/setup-infrastructure.sh` - Infrastructure provisioning (APIs, secrets, service accounts)
- `gcloud/setup-db-instance.sh` - Database VM provisioning (PostgreSQL on Compute Engine)
- `gcloud/deploy-services.sh` - Main deployment script
- `gcloud/cloudbuild.backend.yaml` - Cloud Build for backend
- `gcloud/cloudbuild.frontend.yaml` - Cloud Build for frontend

### Security Features

- Service accounts with minimal permissions
- Secrets stored in Secret Manager
- Private cron endpoints (no public access)
- PostgreSQL with SSL and scram-sha-256 authentication

### Monitoring & Logs

Access via Google Cloud Console:
- **Logs**: Cloud Logging (automatically configured)
- **Metrics**: Cloud Monitoring (auto-scaling metrics)
- **Health**: `/health` endpoint for backend monitoring

### Troubleshooting

**Common issues:**

1. **Build fails**: Check `gcloud auth list` and Docker authentication
2. **Database connection**: Verify Compute Engine DB instance is running (`gcloud compute instances describe multimodal-scout-db --zone=us-central1-a`)
3. **Secrets missing**: Ensure `google-api-key` and `firebase-api-key` are in Secret Manager
4. **Permission errors**: Wait 5-10 minutes for IAM propagation

**Check logs:**
```bash
gcloud logs tail --follow --service multimodal-scout-backend
```

### Scaling Considerations

Current setup auto-scales from 0 to handle traffic spikes:
- **0-100 users/day**: Stay within FREE tier
- **100-1000 users/day**: ~$10-30/month
- **1000+ users/day**: Consider upgrading to a larger Compute Engine instance

### Database Access

The database runs on a Compute Engine e2-micro VM (`multimodal-scout-db`). Access it via SSH tunnel:

```bash
# Open an SSH tunnel (keep this terminal open)
gcloud compute ssh multimodal-scout-db --zone=us-central1-a -- -L 5433:localhost:5432

# In another terminal, connect with psql
DB_PASSWORD=$(gcloud secrets versions access latest --secret="database-password")
PGPASSWORD="$DB_PASSWORD" psql -h 127.0.0.1 -p 5433 -U scout_user -d multimodal_scout
```

Or connect directly (requires psql with SSL support):
```bash
DB_HOST=$(gcloud compute instances describe multimodal-scout-db --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
DB_PASSWORD=$(gcloud secrets versions access latest --secret="database-password")
PGPASSWORD="$DB_PASSWORD" psql "host=$DB_HOST port=5432 user=scout_user dbname=multimodal_scout sslmode=require"
```

**SSH into the VM** (for PostgreSQL admin, logs, etc.):
```bash
gcloud compute ssh multimodal-scout-db --zone=us-central1-a
# Then on the VM:
sudo -u postgres psql                         # admin access
sudo tail -f /var/log/postgresql/postgresql-18-main.log  # logs
```

### Updates & Maintenance

**Deploy new version:**
```bash
gcloud/deploy-services.sh your-project-id us-central1
```

**Database migrations:**
```bash
# Open SSH tunnel
gcloud compute ssh multimodal-scout-db --zone=us-central1-a -- -L 5433:localhost:5432

# In another terminal, run migrations
DB_PASSWORD=$(gcloud secrets versions access latest --secret="database-password")
DATABASE_URL="postgresql://scout_user:$DB_PASSWORD@127.0.0.1:5433/multimodal_scout" alembic upgrade head
```

**Restart PostgreSQL** (if needed):
```bash
gcloud compute ssh multimodal-scout-db --zone=us-central1-a --command="sudo systemctl restart postgresql"
```

### Cost Optimization Tips

1. **Monitor usage** via Cloud Billing dashboard
2. **Scheduled jobs** run only when needed (not continuously)
3. **Auto-scaling to zero** eliminates idle Cloud Run costs
4. **Free-tier VM** eliminates database compute costs
5. **Free tier** covers most small app needs

---

**Perfect for personal projects, MVPs, and low-traffic applications**
**Actual cost for <10 DAU: ~$10-20/month total**
