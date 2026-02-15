#!/bin/bash

# Setup PostgreSQL 18 on Compute Engine e2-micro (free tier)
#
# Prerequisites:
#   - gcloud CLI authenticated
#   - setup-infrastructure.sh already run (enables APIs, creates secrets)
#
# Usage: ./setup-db-instance.sh <project-id> [zone]

set -e

PROJECT_ID=${1:-"your-project-id"}
ZONE=${2:-"us-central1-a"}
INSTANCE_NAME="multimodal-scout-db"

echo "Setting up PostgreSQL 18 on Compute Engine e2-micro (free tier)"
echo "Project: $PROJECT_ID, Zone: $ZONE"
echo ""

# Get database password from Secret Manager
DB_PASSWORD=$(gcloud secrets versions access latest --secret="database-password" --project=$PROJECT_ID 2>/dev/null || true)
if [ -z "$DB_PASSWORD" ]; then
  DB_PASSWORD=$(openssl rand -base64 32)
  echo -n "$DB_PASSWORD" | gcloud secrets create database-password --data-file=- --project=$PROJECT_ID
  echo "Created database-password secret"
fi

# Create the e2-micro instance with PostgreSQL startup script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID &>/dev/null; then
  echo "Instance $INSTANCE_NAME already exists, skipping creation"
else
  echo "Creating Compute Engine instance..."
  gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=e2-micro \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --boot-disk-size=10GB \
    --boot-disk-type=pd-standard \
    --tags=postgres-server \
    --metadata-from-file=startup-script="$SCRIPT_DIR/pg-startup.sh"
fi

# Create firewall rule for PostgreSQL
echo "Creating firewall rule..."
if gcloud compute firewall-rules describe allow-postgres --project=$PROJECT_ID &>/dev/null; then
  echo "Firewall rule already exists, skipping"
else
  gcloud compute firewall-rules create allow-postgres \
    --project=$PROJECT_ID \
    --direction=INGRESS \
    --network=default \
    --action=ALLOW \
    --rules=tcp:5432 \
    --target-tags=postgres-server \
    --source-ranges=0.0.0.0/0 \
    --description="Allow PostgreSQL access (secured by SSL + password auth)"
fi

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready (~60s)..."
PG_READY=false
for i in $(seq 1 12); do
  if gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID \
    --command="sudo -u postgres pg_isready" 2>/dev/null; then
    PG_READY=true
    break
  fi
  echo "  Waiting... ($((i * 10))s)"
  sleep 10
done

if [ "$PG_READY" = false ]; then
  echo "ERROR: PostgreSQL did not start within 120s"
  echo "Check startup logs: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE -- cat /var/log/pg-setup.log"
  exit 1
fi

# Create database and user
echo "Configuring database and user..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command="
  sudo -u postgres psql -c \"CREATE USER scout_user WITH PASSWORD '$DB_PASSWORD';\" 2>/dev/null || \
    sudo -u postgres psql -c \"ALTER USER scout_user WITH PASSWORD '$DB_PASSWORD';\"
  sudo -u postgres psql -c \"CREATE DATABASE multimodal_scout OWNER scout_user;\" 2>/dev/null || \
    echo 'Database already exists'
  sudo -u postgres psql -d multimodal_scout -c \"GRANT ALL ON SCHEMA public TO scout_user;\"
"

# Display connection info
DB_HOST=$(gcloud compute instances describe $INSTANCE_NAME \
  --zone=$ZONE --project=$PROJECT_ID \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "================================================"
echo "PostgreSQL instance ready!"
echo "================================================"
echo ""
echo "  DB_HOST=$DB_HOST"
echo "  DB_PORT=5432"
echo "  DB_USER=scout_user"
echo "  DB_NAME=multimodal_scout"
echo ""
echo "Test connectivity:"
echo "  PGPASSWORD=\$(gcloud secrets versions access latest --secret=database-password) \\"
echo "    psql -h $DB_HOST -U scout_user -d multimodal_scout -c 'SELECT 1'"
echo ""
echo "Next: deploy services with ./deploy-services.sh $PROJECT_ID"
