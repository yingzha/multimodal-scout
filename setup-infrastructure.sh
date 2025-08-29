#!/bin/bash

# Google Cloud Deployment Script for Multimodal Scout
# Cost-optimized setup for low traffic (<10 DAU)

set -e

# Configuration
PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
DB_INSTANCE_NAME="multimodal-scout-db"

echo "🚀 Starting Google Cloud deployment for Multimodal Scout"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"

# Step 1: Enable required APIs
echo "📋 Enabling required APIs..."
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
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

# Step 3: Create Cloud SQL micro instance (cost-optimized)
echo "💾 Creating Cloud SQL micro instance..."
gcloud sql instances create $DB_INSTANCE_NAME \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --storage-type=HDD \
  --storage-size=5GB \
  --backup-start-time=03:00 \
  --maintenance-release-channel=production \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=4 \
  --deletion-protection \
  || echo "Instance already exists"

# Step 4: Create database
echo "🗄️ Creating database..."
gcloud sql databases create multimodal_scout \
  --instance=$DB_INSTANCE_NAME \
  || echo "Database already exists"

# Step 5: Generate database password
echo "🔐 Generating database password..."
DB_PASSWORD=$(openssl rand -base64 32)

# Step 6: Create database user
echo "👤 Creating database user..."
gcloud sql users create scout_user \
  --instance=$DB_INSTANCE_NAME \
  --password="$DB_PASSWORD" \
  || echo "User already exists"

# Step 7: Store secrets
echo "🔐 Storing secrets in Secret Manager..."
echo -n "$DB_PASSWORD" | gcloud secrets create database-password --data-file=-
echo -n "$GOOGLE_API_KEY" | gcloud secrets create google-api-key --data-file=- \
  || echo "Secrets may already exist"

# Step 8: Create service accounts
echo "🔑 Creating service accounts..."
gcloud iam service-accounts create multimodal-scout-backend \
  --display-name="Multimodal Scout Backend Service Account" \
  || echo "Backend service account exists"

gcloud iam service-accounts create multimodal-scout-cron \
  --display-name="Multimodal Scout Cron Service Account" \
  || echo "Cron service account exists"

gcloud iam service-accounts create multimodal-scout-scheduler \
  --display-name="Multimodal Scout Scheduler Service Account" \
  || echo "Scheduler service account exists"

# Step 9: Grant permissions
echo "🛡️ Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:multimodal-scout-backend@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:multimodal-scout-backend@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:multimodal-scout-cron@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:multimodal-scout-cron@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:multimodal-scout-scheduler@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

echo "✅ Infrastructure setup complete!"
echo ""
echo "Next steps:"
echo "1. Deploy services: ./setup-infrastructure.sh $PROJECT_ID $REGION"
echo ""
echo "💰 Estimated monthly cost: $7-10 (Cloud SQL micro instance)"
echo "🎯 Perfect for <10 DAU with auto-scaling to zero"