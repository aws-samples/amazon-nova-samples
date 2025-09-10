#!/bin/bash

# Main Deployment Script for Pipecat ECS
# This script orchestrates the complete deployment process

set -e

# Default values
ENVIRONMENT="test"
AWS_REGION="eu-north-1"
IMAGE_TAG="latest"
SKIP_BUILD="false"
SKIP_DEPLOY="false"
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
    echo -e "${BLUE}[DEPLOY]${NC} $1"
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
    --skip-build)
      SKIP_BUILD="true"
      shift
      ;;
    --skip-deploy)
      SKIP_DEPLOY="true"
      shift
      ;;
    --force-build)
      FORCE_BUILD="true"
      shift
      ;;
    --build-only)
      SKIP_DEPLOY="true"
      shift
      ;;
    --deploy-only)
      SKIP_BUILD="true"
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "This script orchestrates the complete Pipecat ECS deployment process:"
      echo "1. Build and push Docker image to ECR"
      echo "2. Update ECS service with new image"
      echo ""
      echo "Options:"
      echo "  -e, --environment ENV    Set environment (default: test)"
      echo "  -r, --region REGION      Set AWS region (default: eu-north-1)"
      echo "  -t, --tag TAG           Set image tag (default: latest)"
      echo "  --skip-build            Skip Docker build and push"
      echo "  --skip-deploy           Skip ECS service deployment"
      echo "  --force-build           Force rebuild even if image exists"
      echo "  --build-only            Only build and push image"
      echo "  --deploy-only           Only deploy to ECS (skip build)"
      echo "  -h, --help              Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                                    # Full deployment with defaults"
      echo "  $0 -e prod -t v1.2.3                # Deploy to prod with specific tag"
      echo "  $0 --build-only                     # Only build and push image"
      echo "  $0 --deploy-only -t v1.2.3          # Only deploy existing image"
      echo "  $0 --force-build                    # Force rebuild and deploy"
      echo ""
      echo "Prerequisites:"
      echo "  - AWS CLI configured with appropriate credentials"
      echo "  - Docker installed and running"
      echo "  - Infrastructure deployed (run: cd infrastructure && ./deploy.sh)"
      echo "  - Secrets configured in AWS Secrets Manager"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

print_header "Starting Pipecat ECS Deployment"
print_status "Environment: $ENVIRONMENT"
print_status "AWS Region: $AWS_REGION"
print_status "Image Tag: $IMAGE_TAG"
print_status "Skip Build: $SKIP_BUILD"
print_status "Skip Deploy: $SKIP_DEPLOY"

# Validate prerequisites
print_status "Validating prerequisites..."

# Check if we're in the right directory
if [ ! -f "docker/Dockerfile" ] || [ ! -f "server.py" ]; then
    print_error "This script must be run from the pipecat-ecs-deployment directory"
    print_error "Current directory: $(pwd)"
    exit 1
fi

# Check if scripts exist
if [ ! -f "scripts/build-and-push.sh" ] || [ ! -f "scripts/deploy-service.sh" ]; then
    print_error "Deployment scripts not found. Please ensure scripts directory exists."
    exit 1
fi

# Make sure scripts are executable
chmod +x scripts/build-and-push.sh scripts/deploy-service.sh

# Check if infrastructure is deployed
STACK_NAME="PipecatEcsStack-$ENVIRONMENT"
if ! aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION > /dev/null 2>&1; then
    print_warning "Infrastructure stack '$STACK_NAME' not found"
    print_status "Deploying infrastructure first..."
    
    cd infrastructure
    chmod +x deploy.sh
    ./deploy.sh -e $ENVIRONMENT -r $AWS_REGION
    
    if [ $? -ne 0 ]; then
        print_error "Infrastructure deployment failed"
        exit 1
    fi
    
    cd ..
    print_status "Infrastructure deployed successfully!"
    
    # Infrastructure deployment already built and pushed the image, so skip build step
    SKIP_BUILD="true"
fi

print_status "Prerequisites validated successfully!"

# Step 1: Build and push Docker image
if [ "$SKIP_BUILD" = "false" ]; then
    print_header "Step 1: Building and pushing Docker image"
    
    BUILD_ARGS="-e $ENVIRONMENT -r $AWS_REGION -t $IMAGE_TAG"
    if [ "$FORCE_BUILD" = "true" ]; then
        BUILD_ARGS="$BUILD_ARGS --force"
    fi
    
    ./scripts/build-and-push.sh $BUILD_ARGS
    
    if [ $? -ne 0 ]; then
        print_error "Build and push failed"
        exit 1
    fi
    
    print_status "Build and push completed successfully!"
else
    print_warning "Skipping build step as requested"
fi

# Step 2: Deploy to ECS
if [ "$SKIP_DEPLOY" = "false" ]; then
    print_header "Step 2: Deploying to ECS"
    
    ./scripts/deploy-service.sh -e $ENVIRONMENT -r $AWS_REGION -t $IMAGE_TAG --update
    
    if [ $? -ne 0 ]; then
        print_error "ECS deployment failed"
        exit 1
    fi
    
    print_status "ECS deployment completed successfully!"
else
    print_warning "Skipping deployment step as requested"
fi

# Final status and next steps
print_header "Deployment Complete!"

if [ "$SKIP_BUILD" = "false" ] && [ "$SKIP_DEPLOY" = "false" ]; then
    print_status "Full deployment completed successfully!"
elif [ "$SKIP_BUILD" = "true" ]; then
    print_status "Deployment completed (build skipped)"
elif [ "$SKIP_DEPLOY" = "true" ]; then
    print_status "Build completed (deployment skipped)"
fi

# Get application URL
STACK_NAME="PipecatEcsStack-$ENVIRONMENT"
ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDnsName`].OutputValue' \
    --output text 2>/dev/null || echo "Not available")

if [ "$ALB_DNS" != "Not available" ]; then
    print_status "🌐 Application URL: http://$ALB_DNS"
fi

print_status "📋 Next steps:"
print_status "  1. Test the application at the URL above"
print_status "  2. Monitor logs: aws logs tail /ecs/pipecat-voice-agent-$ENVIRONMENT --follow --region $AWS_REGION"
print_status "  3. Check service status: aws ecs describe-services --cluster pipecat-cluster-$ENVIRONMENT --services pipecat-service-$ENVIRONMENT --region $AWS_REGION"

print_header "Deployment script completed!"