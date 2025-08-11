#!/bin/bash
# Script to run cron jobs with proper environment variables

# Source environment variables
export DATABASE_URL="postgresql://scout_user:scout_password@postgres:5432/multimodal_scout"
export PATH="/root/.local/bin:/usr/local/bin:/usr/bin:/bin"

# Load GOOGLE_API_KEY from container environment if available
if [ -n "$1" ]; then
    # Execute the command passed as arguments
    exec "$@"
else
    echo "Usage: $0 <command>"
    exit 1
fi