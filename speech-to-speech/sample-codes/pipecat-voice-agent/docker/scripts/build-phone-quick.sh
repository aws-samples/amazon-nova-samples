#!/bin/bash

# Quick build script using existing ECR repository
# Since server_clean.py handles both WebRTC and phone calls

set -e

ENVIRONMENT="test"
AWS_REGION="eu-north-1"
IMAGE_TAG="latest"
REPO_URI="094271239310.dkr.ecr.eu-north-1.amazonaws.com/pipecat-phone-service-test"

echo "🐳 Building phone service using existing repository"
echo "Repository: $REPO_URI"
echo "Tag: $IMAGE_TAG"

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $REPO_URI

# Build the image for linux/amd64 platform (required for ECS Fargate)
echo "🔨 Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -f ../Dockerfile.phone -t pipecat-phone-service:$IMAGE_TAG ..

# Tag for ECR
echo "🏷️ Tagging for ECR..."
docker tag pipecat-phone-service:$IMAGE_TAG $REPO_URI:$IMAGE_TAG

# Push to ECR
echo "📤 Pushing to ECR..."
docker push $REPO_URI:$IMAGE_TAG

echo "✅ Build complete!"
echo "Image: $REPO_URI:$IMAGE_TAG"
echo ""
echo "Next: Update your ECS service to use this image"