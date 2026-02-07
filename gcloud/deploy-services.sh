#!/bin/bash

# Build Images and Deploy Services to Google Cloud
# Complete build and deployment process

set -e

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
DB_INSTANCE_NAME="multimodal-scout-db"
FIREBASE_API_KEY=$(gcloud secrets versions access latest --secret="firebase-api-key" --project="$PROJECT_ID" 2>/dev/null || echo "")
if [ -z "$FIREBASE_API_KEY" ]; then
  echo "❌ firebase-api-key not found in Secret Manager"
  echo "   Create it with: echo -n 'YOUR_KEY' | gcloud secrets create firebase-api-key --data-file=- --project=$PROJECT_ID"
  exit 1
fi
FIREBASE_PROJECT_ID=$(gcloud secrets versions access latest --secret="firebase-project-id" --project="$PROJECT_ID" 2>/dev/null || echo "$PROJECT_ID")
FIREBASE_AUTH_DOMAIN="$FIREBASE_PROJECT_ID.firebaseapp.com"

echo "🚀 Building images and deploying services for Multimodal Scout"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"

# Configure Docker for Artifact Registry
echo "🔐 Configuring Docker authentication..."
gcloud auth configure-docker $REGION-docker.pkg.dev

# Build and push backend image
echo "🏗️ Building backend image..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

gcloud builds submit \
  --config "$SCRIPT_DIR/cloudbuild.backend.yaml" \
  --substitutions _IMAGE_NAME=$REGION-docker.pkg.dev/$PROJECT_ID/multimodal-scout/backend:latest \
  "$PROJECT_ROOT"

echo "✅ Backend image built and pushed successfully!"
echo ""

# Get Cloud SQL connection name
CONNECTION_NAME="$PROJECT_ID:$REGION:$DB_INSTANCE_NAME"

# Deploy backend service first
echo "🖥️ Deploying backend service..."
gcloud run deploy multimodal-scout-backend \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/multimodal-scout/backend:latest \
  --platform managed \
  --region $REGION \
  --service-account multimodal-scout-backend@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
  --set-env-vars FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID \
  --set-env-vars DB_USER=scout_user \
  --set-env-vars DB_NAME=multimodal_scout \
  --set-env-vars INSTANCE_CONNECTION_NAME=$CONNECTION_NAME \
  --add-cloudsql-instances $CONNECTION_NAME \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 10 \
  --cpu-boost \
  --port 8000 \
  --allow-unauthenticated

# Get actual backend URL
BACKEND_URL=$(gcloud run services describe multimodal-scout-backend \
  --region $REGION \
  --format 'value(status.url)')

echo "🖥️ Backend deployed at: $BACKEND_URL"

# Now build and push frontend image with correct backend URL
echo "🏗️ Building frontend image with backend URL..."
gcloud builds submit \
  --config "$SCRIPT_DIR/cloudbuild.frontend.yaml" \
  --substitutions _IMAGE_NAME=$REGION-docker.pkg.dev/$PROJECT_ID/multimodal-scout/frontend:latest,_BACKEND_URL=$BACKEND_URL,_FIREBASE_API_KEY=$FIREBASE_API_KEY,_FIREBASE_AUTH_DOMAIN=$FIREBASE_AUTH_DOMAIN,_FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID \
  "$PROJECT_ROOT"

echo "✅ Frontend image built and pushed successfully!"

# Deploy frontend service
echo "🌐 Deploying frontend service..."
gcloud run deploy multimodal-scout-frontend \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/multimodal-scout/frontend:latest \
  --platform managed \
  --region $REGION \
  --set-env-vars NEXT_PUBLIC_API_URL=$BACKEND_URL \
  --set-env-vars NODE_ENV=production \
  --cpu 1 \
  --memory 1Gi \
  --min-instances 1 \
  --max-instances 5 \
  --allow-unauthenticated

# Cron service deployment removed - using Cloud Scheduler → Backend /pipeline endpoint

# Get URLs
FRONTEND_URL=$(gcloud run services describe multimodal-scout-frontend \
  --region $REGION \
  --format 'value(status.url)')

# Deploy Cloud Scheduler job (create or update)
echo "⏰ Setting up Cloud Scheduler job..."

# Get pipeline secret from Secret Manager for scheduler
PIPELINE_SECRET=$(gcloud secrets versions access latest --secret="pipeline-secret" 2>/dev/null || echo "")
if [ -z "$PIPELINE_SECRET" ]; then
  echo "⚠️  Warning: pipeline-secret not found in Secret Manager"
  echo "   Create it with: gcloud secrets create pipeline-secret --data-file=<(echo 'your-random-secret')"
  echo "   Using placeholder - update after secret creation"
  PIPELINE_SECRET="PLACEHOLDER_UPDATE_AFTER_SECRET_CREATION"
fi

if gcloud scheduler jobs describe pipeline-job --location=$REGION &>/dev/null; then
  echo "📝 Updating existing scheduler job with pipeline authentication..."
  gcloud scheduler jobs update http pipeline-job \
    --location=$REGION \
    --schedule="*/30 * * * *" \
    --uri="$BACKEND_URL/pipeline" \
    --http-method=POST \
    --update-headers="Authorization=Bearer $PIPELINE_SECRET" \
    --clear-auth-token \
    --time-zone="UTC"
  echo "✅ Scheduler job updated successfully"
else
  echo "➕ Creating new scheduler job with pipeline authentication..."
  gcloud scheduler jobs create http pipeline-job \
    --location=$REGION \
    --schedule="*/30 * * * *" \
    --uri="$BACKEND_URL/pipeline" \
    --http-method=POST \
    --headers="Authorization=Bearer $PIPELINE_SECRET" \
    --time-zone="UTC"
  echo "✅ Scheduler job created successfully"
fi

echo ""
echo "✅ Complete deployment finished!"
echo ""
echo "🌐 Frontend URL: $FRONTEND_URL"
echo "🖥️ Backend URL: $BACKEND_URL"
echo "⏰ Pipeline Endpoint: $BACKEND_URL/pipeline"
echo "📅 Scheduler Job: pipeline-job (runs every 30 minutes)"
echo ""
echo "💡 Next steps:"
echo "1. Run database migrations if needed" 
echo "2. Test the application"
echo ""
echo "💰 Estimated cost: $5-8/month for <10 DAU"