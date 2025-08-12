#!/bin/bash
# Google Cloud Platform setup script for Multimodal Scout

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-your-project-id}"
REGION="${REGION:-us-central1}"
DATABASE_INSTANCE="multimodal-scout-db"
DATABASE_NAME="multimodal_scout"
DATABASE_USER="scout_user"

echo "🚀 Setting up Multimodal Scout on Google Cloud Platform"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"

# Enable required APIs
echo "📡 Enabling required Google Cloud APIs..."
gcloud services enable run.googleapis.com \
  sqladmin.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  artifactregistry.googleapis.com \
  --project=$PROJECT_ID

# Create Artifact Registry repository
echo "📦 Creating Artifact Registry repository..."
gcloud artifacts repositories create multimodal-scout \
  --repository-format=docker \
  --location=$REGION \
  --project=$PROJECT_ID || echo "Repository may already exist"

# Create Cloud SQL instance
echo "🗄️ Creating Cloud SQL PostgreSQL instance..."
gcloud sql instances create $DATABASE_INSTANCE \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --storage-type=SSD \
  --storage-size=10GB \
  --storage-auto-increase \
  --backup-start-time=03:00 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=04 \
  --project=$PROJECT_ID || echo "Instance may already exist"

# Create database user
echo "👤 Creating database user..."
DATABASE_PASSWORD=$(openssl rand -base64 32)
gcloud sql users create $DATABASE_USER \
  --instance=$DATABASE_INSTANCE \
  --password=$DATABASE_PASSWORD \
  --project=$PROJECT_ID || echo "User may already exist"

# Create database
echo "🗃️ Creating database..."
gcloud sql databases create $DATABASE_NAME \
  --instance=$DATABASE_INSTANCE \
  --project=$PROJECT_ID || echo "Database may already exist"

# Store secrets in Secret Manager
echo "🔐 Storing secrets in Secret Manager..."
echo -n "$DATABASE_PASSWORD" | gcloud secrets create database-password \
  --data-file=- \
  --project=$PROJECT_ID || echo "Secret may already exist"

echo -n "${GOOGLE_API_KEY:-}" | gcloud secrets create google-api-key \
  --data-file=- \
  --project=$PROJECT_ID || echo "Secret may already exist (please update manually)"

# Get Cloud SQL connection name
CONNECTION_NAME=$(gcloud sql instances describe $DATABASE_INSTANCE \
  --project=$PROJECT_ID \
  --format="value(connectionName)")

echo "✅ Google Cloud setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Update your environment variables:"
echo "   export PROJECT_ID=$PROJECT_ID"
echo "   export DATABASE_CONNECTION_NAME=$CONNECTION_NAME"
echo ""
echo "2. If you haven't set your Google API key:"
echo "   gcloud secrets versions add google-api-key --data-file=<(echo -n 'YOUR_API_KEY')"
echo ""
echo "3. Deploy the application:"
echo "   gcloud builds submit --config cloudbuild.yaml"
echo ""
echo "4. Set up Cloud Scheduler jobs (after deployment):"
echo "   ./deployment/setup-scheduler.sh"