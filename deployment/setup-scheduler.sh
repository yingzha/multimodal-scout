#!/bin/bash
# Setup Cloud Scheduler jobs for Multimodal Scout

set -e

PROJECT_ID="${PROJECT_ID:-your-project-id}"
REGION="${REGION:-us-central1}"
CRON_SERVICE_URL="https://multimodal-scout-cron-$(gcloud config get-value project)-uc.a.run.app"

echo "⏰ Setting up Cloud Scheduler jobs"
echo "Cron service URL: $CRON_SERVICE_URL"

# Create service account for Cloud Scheduler
echo "👤 Creating service account for Cloud Scheduler..."
gcloud iam service-accounts create cloud-scheduler-sa \
  --display-name="Cloud Scheduler Service Account" \
  --project=$PROJECT_ID || echo "Service account may already exist"

# Grant Cloud Run Invoker role to service account
gcloud run services add-iam-policy-binding multimodal-scout-cron \
  --member="serviceAccount:cloud-scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=$REGION \
  --project=$PROJECT_ID

# Create Hacker News hourly job
echo "📰 Creating Hacker News hourly scheduler job..."
gcloud scheduler jobs create http hacker-news-hourly \
  --schedule="0 * * * *" \
  --uri="$CRON_SERVICE_URL/cron/hacker-news" \
  --http-method=POST \
  --oidc-service-account-email="cloud-scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --location=$REGION \
  --project=$PROJECT_ID || echo "Job may already exist"

# Create Hugging Face 6-hour job
echo "🤗 Creating Hugging Face 6-hourly scheduler job..."
gcloud scheduler jobs create http hugging-face-6hourly \
  --schedule="0 */6 * * *" \
  --uri="$CRON_SERVICE_URL/cron/hugging-face" \
  --http-method=POST \
  --oidc-service-account-email="cloud-scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --location=$REGION \
  --project=$PROJECT_ID || echo "Job may already exist"

echo "✅ Cloud Scheduler setup complete!"
echo ""
echo "📋 Scheduled jobs:"
echo "• Hacker News: Every hour"
echo "• Hugging Face: Every 6 hours"