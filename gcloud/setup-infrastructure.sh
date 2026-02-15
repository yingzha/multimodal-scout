#!/bin/bash

# Google Cloud Deployment Script for Multimodal Scout
# Cost-optimized setup for low traffic (<10 DAU)

set -e

# Configuration
PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}

echo "🚀 Starting Google Cloud deployment for Multimodal Scout"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"

# Step 1: Enable required APIs
echo "📋 Enabling required APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  compute.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  artifactregistry.googleapis.com

# Step 2: Create Artifact Registry repository
echo "📦 Creating Artifact Registry repository..."
gcloud artifacts repositories create multimodal-scout \
  --repository-format=docker \
  --location=$REGION \
  --description="Multimodal Scout container images" \
  || echo "Repository already exists"

# Step 3: Store secrets
echo "🔐 Storing secrets in Secret Manager..."

# Database password (may already exist from setup-db-instance.sh)
if ! gcloud secrets describe database-password --project=$PROJECT_ID &>/dev/null; then
  DB_PASSWORD=$(openssl rand -base64 32)
  echo -n "$DB_PASSWORD" | gcloud secrets create database-password --data-file=-
  echo "Created database-password secret"
else
  echo "database-password secret already exists"
fi

echo -n "$GOOGLE_API_KEY" | gcloud secrets create google-api-key --data-file=- \
  || echo "google-api-key secret already exists"

# Generate and store pipeline secret
if ! gcloud secrets describe pipeline-secret --project=$PROJECT_ID &>/dev/null; then
  PIPELINE_SECRET=$(openssl rand -base64 32)
  echo -n "$PIPELINE_SECRET" | gcloud secrets create pipeline-secret --data-file=-
  echo "Created pipeline-secret"
else
  echo "pipeline-secret already exists"
fi

# Step 4: Create service accounts
echo "🔑 Creating service accounts..."
gcloud iam service-accounts create multimodal-scout-backend \
  --display-name="Multimodal Scout Backend Service Account" \
  || echo "Backend service account exists"

gcloud iam service-accounts create multimodal-scout-scheduler \
  --display-name="Multimodal Scout Scheduler Service Account" \
  || echo "Scheduler service account exists"

# Step 5: Grant permissions
echo "🛡️ Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:multimodal-scout-backend@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:multimodal-scout-scheduler@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

echo "✅ Infrastructure setup complete!"
echo ""
echo "Next steps:"
echo "1. Setup database: ./setup-db-instance.sh $PROJECT_ID ${REGION}-a"
echo "2. Deploy services: ./deploy-services.sh $PROJECT_ID $REGION"
echo ""
echo "💰 Estimated monthly cost: ~\$10-20 (DB VM free tier, Cloud Run ~\$6-8, Gemini API ~\$3-8)"
echo "🎯 Perfect for <10 DAU with auto-scaling to zero"
