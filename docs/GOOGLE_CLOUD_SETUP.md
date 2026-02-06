# 🚀 Google Cloud Migration Guide

## Cost-Optimized Setup for Low Traffic (<10 DAU)

**Total Estimated Cost: $7-10/month**

### 📋 Prerequisites

1. Google Cloud account with billing enabled
2. `gcloud` CLI installed and authenticated
3. Docker installed locally
4. Google API key (Gemini) stored in Secret Manager
5. Firebase project configured with Google Sign-In enabled
6. Firebase API key stored in Secret Manager (`firebase-api-key`)

### 🚀 Quick Start

1. **Clone and prepare project:**
```bash
cd multimodal-scout
export GOOGLE_API_KEY="your-gemini-api-key-here"
```

2. **Run the complete setup:**
```bash
# Replace with your actual project ID
./setup-infrastructure.sh your-project-id us-central1
gcloud/deploy-services.sh your-project-id us-central1
```

3. **That's it!** Your app will be running on Google Cloud.

### 🏗️ Architecture Overview

- **Frontend**: Cloud Run (Next.js) - Auto-scales to 0, FREE for <10 DAU
- **Backend**: Cloud Run (FastAPI) - Auto-scales to 0, FREE for <10 DAU  
- **Database**: Cloud SQL Micro (PostgreSQL) - $7/month fixed cost
- **Cron Jobs**: Cloud Scheduler + Cloud Run Jobs - FREE for low frequency
- **Secrets**: Secret Manager - 6 secrets FREE
- **Images**: Artifact Registry - FREE tier


### ⚙️ Services Created

**Cloud Run Services:**
- `multimodal-scout-backend` - FastAPI API server
- `multimodal-scout-frontend` - Next.js web app
- **Pipeline**: Cloud Scheduler calls `POST /pipeline` every 30 minutes (no separate cron service)

**Cloud SQL:**
- Instance: `multimodal-scout-db` (micro, PostgreSQL 17)
- Database: `multimodal_scout`
- User: `scout_user`

**Scheduled Jobs:**
- Pipeline: Every 30 minutes via Cloud Scheduler

### 🔧 Configuration Files

- `gcloud/deploy-services.sh` - Main deployment script
- `gcloud/cloudbuild.backend.yaml` - Cloud Build for backend
- `gcloud/cloudbuild.frontend.yaml` - Cloud Build for frontend

### 🔐 Security Features

- Service accounts with minimal permissions
- Secrets stored in Secret Manager
- Private cron endpoints (no public access)
- Cloud SQL with encrypted connections

### 📊 Monitoring & Logs

Access via Google Cloud Console:
- **Logs**: Cloud Logging (automatically configured)
- **Metrics**: Cloud Monitoring (auto-scaling metrics)
- **Health**: `/health` endpoint for backend monitoring

### 🚨 Troubleshooting

**Common issues:**

1. **Build fails**: Check `gcloud auth list` and Docker authentication
2. **Database connection**: Verify Cloud SQL instance is running
3. **Secrets missing**: Ensure `google-api-key` and `firebase-api-key` are in Secret Manager
4. **Permission errors**: Wait 5-10 minutes for IAM propagation

**Check logs:**
```bash
gcloud logs tail --follow --service multimodal-scout-backend
```

### 📈 Scaling Considerations

Current setup auto-scales from 0 to handle traffic spikes:
- **0-100 users/day**: Stay within FREE tier
- **100-1000 users/day**: ~$10-30/month  
- **1000+ users/day**: Consider upgrading Cloud SQL instance

### 🔄 Updates & Maintenance

**Deploy new version:**
```bash
gcloud/deploy-services.sh your-project-id us-central1
```

**Database migrations:**
```bash
gcloud sql connect multimodal-scout-db --user=scout_user
# Run your SQL migrations here
```

### 💡 Cost Optimization Tips

1. **Monitor usage** via Cloud Billing dashboard
2. **Scheduled jobs** run only when needed (not continuously)
3. **Auto-scaling to zero** eliminates idle costs
4. **Micro instance** is perfect for <10 DAU
5. **Free tier** covers most small app needs

---

**✅ Perfect for personal projects, MVPs, and low-traffic applications**
**🎯 Actual cost for <10 DAU: ~$7-10/month total**