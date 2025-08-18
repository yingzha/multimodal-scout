#!/bin/bash
# Script to run cron jobs with proper environment variables

# Set PATH for cron environment
export PATH="/root/.local/bin:/usr/local/bin:/usr/bin:/bin"

# Pass through environment variables from container environment
# (These are set via docker-compose.yml environment section)
export DATABASE_URL="${DATABASE_URL}"
export GOOGLE_API_KEY="${GOOGLE_API_KEY}"
export DEBUG="${DEBUG:-false}"

# Verify required environment variables
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "ERROR: GOOGLE_API_KEY environment variable is not set"
    echo "Please ensure it's defined in docker-compose.yml environment section or .env file"
    exit 1
fi

echo "Environment loaded successfully. API key: ${GOOGLE_API_KEY:0:10}..."

if [ -n "$1" ]; then
    # Execute the command passed as arguments
    exec "$@"
else
    echo "Usage: $0 <command>"
    exit 1
fi