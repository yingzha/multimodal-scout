#!/bin/bash

# Build and Deploy Images to Google Cloud
# Cost-optimized build process

set -e

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}

echo "🏗️ Building and deploying images for Multimodal Scout"
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

# Build and push cron image
echo "🏗️ Building cron image..."
gcloud builds submit \
  --tag $REGION-docker.pkg.dev/$PROJECT_ID/multimodal-scout/cron:latest \
  --file Dockerfile.cron \
  .

echo "✅ All images built and pushed successfully!"
echo ""
echo "Next: Deploy services with ./deploy-services.sh $PROJECT_ID $REGION"