#!/bin/bash

# Backend Deployment Script
# Builds and deploys the backend to ECS

set -e

# Configuration
BACKEND_DIR="backend"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPOSITORY="${ECR_REPOSITORY:-zappix-demo2-production-backend}"
ECS_CLUSTER="${ECS_CLUSTER:-zappix-demo2-production-cluster}"
ECS_SERVICE="${ECS_SERVICE:-zappix-demo2-production-backend}"

echo "🚀 Deploying Zappix Demo Backend"
echo "================================="

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Navigate to backend directory
cd "$BACKEND_DIR"

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_REGISTRY

# Build Docker image
echo "🔨 Building Docker image..."
IMAGE_TAG=$(git rev-parse --short HEAD)
docker build -t "$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" .
docker tag "$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" "$ECR_REGISTRY/$ECR_REPOSITORY:latest"

# Push to ECR
echo "📤 Pushing to ECR..."
docker push "$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"
docker push "$ECR_REGISTRY/$ECR_REPOSITORY:latest"

# Update ECS service
echo "🔄 Updating ECS service..."
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $ECS_SERVICE \
    --force-new-deployment

# Wait for deployment
echo "⏳ Waiting for deployment to complete..."
aws ecs wait services-stable \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE

echo "✅ Backend deployment complete!"
echo "   URL: https://zappix2-backend.aldea.ai"

