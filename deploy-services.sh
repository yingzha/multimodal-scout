#!/bin/bash

# Build Images and Deploy Services to Google Cloud
# Complete build and deployment process

set -e

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
DB_INSTANCE_NAME="multimodal-scout-db"

echo "🚀 Building images and deploying services for Multimodal Scout"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"

# Configure Docker for Artifact Registry
echo "🔐 Configuring Docker authentication..."
gcloud auth configure-docker $REGION-docker.pkg.dev

# Build and push backend image
echo "🏗️ Building backend image..."
gcloud builds submit \
  --tag $REGION-docker.pkg.dev/$PROJECT_ID/multimodal-scout/backend:latest \
  --file Dockerfile.backend \
  .

# Build and push frontend image  
echo "🏗️ Building frontend image..."
gcloud builds submit \
  --tag $REGION-docker.pkg.dev/$PROJECT_ID/multimodal-scout/frontend:latest \
  --file Dockerfile.frontend \
  .

# Cron service removed - using Cloud Scheduler → Backend /pipeline endpoint

echo "✅ All images built and pushed successfully!"
echo ""

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

# Cron service deployment removed - using Cloud Scheduler → Backend /pipeline endpoint

# Get URLs
FRONTEND_URL=$(gcloud run services describe multimodal-scout-frontend \
  --region $REGION \
  --format 'value(status.url)')

echo ""
echo "✅ Complete deployment finished!"
echo ""
echo "🌐 Frontend URL: $FRONTEND_URL"
echo "🖥️ Backend URL: $BACKEND_URL"
echo "⏰ Pipeline Endpoint: $BACKEND_URL/pipeline"
echo ""
echo "💡 Next steps:"
echo "1. Set up Cloud Scheduler jobs (replace HASH in cloud-scheduler-jobs.yaml)"
echo "2. Run database migrations if needed" 
echo "3. Test the application"
echo ""
echo "💰 Estimated cost: $5-8/month for <10 DAU (reduced without cron service)"