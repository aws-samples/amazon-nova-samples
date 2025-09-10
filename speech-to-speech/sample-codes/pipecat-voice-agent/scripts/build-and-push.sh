#!/bin/bash

# Build and push script for Pipecat Voice Agent container

set -e

# Default values
ENVIRONMENT="test"
AWS_REGION="eu-north-1"
IMAGE_TAG="latest"
FORCE_BUILD=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -r|--region)
      AWS_REGION="$2"
      shift 2
      ;;
    -t|--tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --force)
      FORCE_BUILD=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  -e, --environment ENV    Set environment (default: test)"
      echo "  -r, --region REGION     Set AWS region (default: eu-north-1)"
      echo "  -t, --tag TAG           Set image tag (default: latest)"
      echo "  --force                 Force rebuild"
      echo "  -h, --help              Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

REPO_URI="094271239310.dkr.ecr.$AWS_REGION.amazonaws.com/pipecat-voice-agent-$ENVIRONMENT"

echo "🐳 Building and pushing Pipecat Voice Agent container"
echo "Repository: $REPO_URI"
echo "Tag: $IMAGE_TAG"
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $REPO_URI

# Build the image for linux/amd64 platform (required for ECS Fargate)
echo "🔨 Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -t pipecat-voice-agent:$IMAGE_TAG .

# Tag for ECR
echo "🏷️ Tagging for ECR..."
docker tag pipecat-voice-agent:$IMAGE_TAG $REPO_URI:$IMAGE_TAG

# Push to ECR
echo "📤 Pushing to ECR..."
docker push $REPO_URI:$IMAGE_TAG

echo "✅ Build and push complete!"
echo "Image: $REPO_URI:$IMAGE_TAG"
echo ""
echo "Next: Update your ECS service to use this image"