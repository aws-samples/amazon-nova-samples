#!/bin/bash

# Build and Push Script for Pipecat Phone Service
# This script builds the phone service container and pushes it to ECR

set -e

# Default values
ENVIRONMENT="test"
AWS_REGION="eu-north-1"
IMAGE_TAG="latest"
FORCE_BUILD="false"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[BUILD-PHONE]${NC} $1"
}

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
      FORCE_BUILD="true"
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "This script builds and pushes the Pipecat Phone Service Docker image:"
      echo "1. Build phone service Docker image using Dockerfile.phone"
      echo "2. Tag and push to ECR repository"
      echo ""
      echo "Options:"
      echo "  -e, --environment ENV    Set environment (default: test)"
      echo "  -r, --region REGION      Set AWS region (default: eu-north-1)"
      echo "  -t, --tag TAG           Set image tag (default: latest)"
      echo "  --force                 Force rebuild even if image exists"
      echo "  -h, --help              Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                      # Build with defaults"
      echo "  $0 -e prod -t v1.2.3   # Build for prod with specific tag"
      echo "  $0 --force             # Force rebuild"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

print_header "Building Pipecat Phone Service"
print_status "Environment: $ENVIRONMENT"
print_status "AWS Region: $AWS_REGION"
print_status "Image Tag: $IMAGE_TAG"
print_status "Force Build: $FORCE_BUILD"

# Validate prerequisites
print_status "Validating prerequisites..."

# Check if we're in the right directory
if [ ! -f "docker/Dockerfile.phone" ] || [ ! -f "server_clean.py" ]; then
    print_error "This script must be run from the pipecat-ecs-deployment directory"
    print_error "Current directory: $(pwd)"
    exit 1
fi

# Check if infrastructure is deployed
STACK_NAME="PipecatEcsStack-$ENVIRONMENT"
if ! aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION > /dev/null 2>&1; then
    print_error "Infrastructure stack '$STACK_NAME' not found"
    print_error "Please deploy the infrastructure first"
    exit 1
fi

# Get ECR repository URI
PHONE_REPO_URI=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`PhoneRepositoryUri`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ -z "$PHONE_REPO_URI" ]; then
    print_error "Phone service repository not found in infrastructure"
    print_error "Please redeploy infrastructure with phone service support"
    exit 1
fi

print_status "Phone Repository URI: $PHONE_REPO_URI"
print_status "Prerequisites validated successfully!"

# Login to ECR
print_status "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $PHONE_REPO_URI

# Check if image already exists
if [ "$FORCE_BUILD" = "false" ]; then
    if aws ecr describe-images --repository-name $(basename $PHONE_REPO_URI) --image-ids imageTag=$IMAGE_TAG --region $AWS_REGION > /dev/null 2>&1; then
        print_warning "Image with tag '$IMAGE_TAG' already exists in ECR"
        print_status "Use --force to rebuild anyway"
        exit 0
    fi
fi

# Build the phone service image
print_header "Building phone service Docker image"
print_status "Using Dockerfile.phone..."

docker build -f docker/Dockerfile.phone -t pipecat-phone-service:$IMAGE_TAG .

if [ $? -ne 0 ]; then
    print_error "Docker build failed"
    exit 1
fi

print_status "Docker build completed successfully!"

# Tag for ECR
print_status "Tagging image for ECR..."
docker tag pipecat-phone-service:$IMAGE_TAG $PHONE_REPO_URI:$IMAGE_TAG

# Push to ECR
print_header "Pushing image to ECR"
print_status "Pushing to: $PHONE_REPO_URI:$IMAGE_TAG"

docker push $PHONE_REPO_URI:$IMAGE_TAG

if [ $? -ne 0 ]; then
    print_error "Docker push failed"
    exit 1
fi

print_status "Docker push completed successfully!"

# Final status
print_header "Build Complete!"
print_status "✅ Phone service image built and pushed successfully"
print_status "📦 Image: $PHONE_REPO_URI:$IMAGE_TAG"
print_status ""
print_status "📋 Next steps:"
print_status "  1. Deploy the service: ./scripts/deployment/deploy-phone-service.sh --deploy-only -t $IMAGE_TAG"
print_status "  2. Or run full deployment: ./scripts/deployment/deploy-phone-service.sh"

print_header "Build script completed!"