#!/bin/bash

# Deploy Cloud Run Services
# Final deployment step

set -e

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
DB_INSTANCE_NAME="multimodal-scout-db"

echo "🚀 Deploying Cloud Run services for Multimodal Scout"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"

# Get Cloud SQL connection name
CONNECTION_NAME="$PROJECT_ID:$REGION:$DB_INSTANCE_NAME"

# Deploy backend service
echo "🖥️ Deploying backend service..."
gcloud run deploy multimodal-scout-backend \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/multimodal-scout/backend:latest \
  --platform managed \
  --region $REGION \
  --service-account multimodal-scout-backend@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
  --set-env-vars DB_USER=scout_user \
  --set-env-vars DB_NAME=multimodal_scout \
  --set-env-vars INSTANCE_CONNECTION_NAME=$CONNECTION_NAME \
  --add-cloudsql-instances $CONNECTION_NAME \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 10 \
  --port 8000 \
  --allow-unauthenticated

# Get backend URL for frontend
BACKEND_URL=$(gcloud run services describe multimodal-scout-backend \
  --region $REGION \
  --format 'value(status.url)')

# Deploy frontend service
echo "🌐 Deploying frontend service..."
gcloud run deploy multimodal-scout-frontend \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/multimodal-scout/frontend:latest \
  --platform managed \
  --region $REGION \
  --set-env-vars NEXT_PUBLIC_API_URL=$BACKEND_URL \
  --set-env-vars NODE_ENV=production \
  --cpu 1 \
  --memory 256Mi \
  --min-instances 0 \
  --max-instances 5 \
  --port 3000 \
  --allow-unauthenticated

# Deploy cron job service (for scheduler to trigger)
echo "⏰ Deploying cron job service..."
gcloud run deploy multimodal-scout-cron \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/multimodal-scout/cron:latest \
  --platform managed \
  --region $REGION \
  --service-account multimodal-scout-cron@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
  --set-env-vars DB_USER=scout_user \
  --set-env-vars DB_NAME=multimodal_scout \
  --set-env-vars INSTANCE_CONNECTION_NAME=$CONNECTION_NAME \
  --add-cloudsql-instances $CONNECTION_NAME \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 1 \
  --no-allow-unauthenticated

# Get URLs
FRONTEND_URL=$(gcloud run services describe multimodal-scout-frontend \
  --region $REGION \
  --format 'value(status.url)')

CRON_URL=$(gcloud run services describe multimodal-scout-cron \
  --region $REGION \
  --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Frontend URL: $FRONTEND_URL"
echo "🖥️ Backend URL: $BACKEND_URL"
echo "⏰ Cron URL: $CRON_URL"
echo ""
echo "💡 Next steps:"
echo "1. Set up Cloud Scheduler jobs (update URLs in cloud-scheduler-jobs.yaml)"
echo "2. Run database migrations if needed"
echo "3. Test the application"
echo ""
echo "💰 Estimated cost: $7-10/month for <10 DAU"