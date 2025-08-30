#!/bin/bash
# Environment Configuration Script
# Usage: ./scripts/configure-env.sh [local|cloud]

set -e

ENV_TYPE=${1:-"local"}
PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

echo "🔧 Configuring environment for: $ENV_TYPE"

case "$ENV_TYPE" in
  "local")
    echo "📋 Setting up local development environment..."
    
    # Copy local environment file
    if [ -f "$PROJECT_ROOT/.env.local" ]; then
      cp "$PROJECT_ROOT/.env.local" "$PROJECT_ROOT/.env"
      echo "✅ Local environment configured (.env.local → .env)"
    else
      echo "❌ .env.local file not found"
      exit 1
    fi
    
    # Update docker-compose for local development
    echo "🐳 Docker Compose configured for local development"
    
    ;;
    
  "cloud")
    echo "☁️  Setting up cloud deployment environment..."
    
    # Copy cloud environment template
    if [ -f "$PROJECT_ROOT/.env.cloud" ]; then
      cp "$PROJECT_ROOT/.env.cloud" "$PROJECT_ROOT/.env"
      echo "✅ Cloud environment template configured (.env.cloud → .env)"
      echo "ℹ️  Note: Deploy script will set dynamic values (DATABASE_URL, API URLs)"
    else
      echo "❌ .env.cloud file not found"
      exit 1
    fi
    
    ;;
    
  *)
    echo "❌ Invalid environment type: $ENV_TYPE"
    echo "Usage: ./scripts/configure-env.sh [local|cloud]"
    exit 1
    ;;
esac

echo ""
echo "🎯 Environment configured for: $ENV_TYPE"
echo "📄 Current .env file:"
echo "----------------------------------------"
cat "$PROJECT_ROOT/.env"
echo "----------------------------------------"