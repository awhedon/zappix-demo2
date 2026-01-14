#!/bin/bash

# Frontend Deployment Script
# Builds and deploys the frontend to S3/CloudFront

set -e

# Configuration
FRONTEND_DIR="frontend"
S3_BUCKET="${FRONTEND_BUCKET:-zappix-demo2-production-frontend}"
CLOUDFRONT_DISTRIBUTION_ID="${CLOUDFRONT_DISTRIBUTION_ID}"
API_URL="${API_URL:-https://zappix2-backend.aldea.ai}"

echo "🚀 Deploying Zappix Demo Frontend"
echo "================================="

# Check required variables
if [ -z "$CLOUDFRONT_DISTRIBUTION_ID" ]; then
    echo "❌ Error: CLOUDFRONT_DISTRIBUTION_ID is not set"
    exit 1
fi

# Navigate to frontend directory
cd "$FRONTEND_DIR"

# Install dependencies
echo "📦 Installing dependencies..."
npm ci

# Build the application
echo "🔨 Building application..."
NEXT_PUBLIC_API_URL=$API_URL npm run build

# Sync to S3
echo "📤 Uploading to S3..."
aws s3 sync out "s3://$S3_BUCKET" \
    --delete \
    --cache-control "public, max-age=31536000, immutable" \
    --exclude "*.html"

aws s3 sync out "s3://$S3_BUCKET" \
    --delete \
    --cache-control "public, max-age=0, must-revalidate" \
    --include "*.html"

# Invalidate CloudFront cache
echo "🔄 Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
    --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
    --paths "/*"

echo "✅ Frontend deployment complete!"
echo "   URL: https://zappix2.aldea.ai"

