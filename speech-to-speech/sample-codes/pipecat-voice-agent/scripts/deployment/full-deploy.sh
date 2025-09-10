#!/bin/bash

# Complete Pipecat ECS Deployment Script
# This script handles the complete deployment flow:
# 1. Set up secrets in AWS Secrets Manager
# 2. Deploy infrastructure (ECR, ECS, ALB, etc.)
# 3. Build and push Docker image
# 4. Deploy/update ECS service

set -e

# Default values
ENVIRONMENT="test"
AWS_REGION="eu-north-1"
IMAGE_TAG="latest"

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
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Complete deployment script for Pipecat ECS deployment"
      echo ""
      echo "Options:"
      echo "  -e, --environment ENV    Set environment (default: test)"
      echo "  -r, --region REGION      Set AWS region (default: eu-north-1)"
      echo "  -t, --tag TAG           Set image tag (default: latest)"
      echo "  -h, --help              Show this help message"
      echo ""
      echo "This script will:"
      echo "  1. Set up AWS Secrets Manager secrets"
      echo "  2. Deploy CDK infrastructure"
      echo "  3. Build and push Docker image to ECR"
      echo "  4. Deploy ECS service"
      echo ""
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

print_header "🚀 Starting Complete Pipecat ECS Deployment"
print_status "Environment: $ENVIRONMENT"
print_status "AWS Region: $AWS_REGION"
print_status "Image Tag: $IMAGE_TAG"
echo ""

# Check prerequisites
print_status "Checking prerequisites..."

# Check if we're in the right directory
if [ ! -f "docker/Dockerfile" ] || [ ! -f "server.py" ]; then
    print_error "This script must be run from the pipecat-ecs-deployment directory"
    print_error "Current directory: $(pwd)"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    print_error "AWS CLI is not configured or credentials are invalid"
    print_error "Please run 'aws configure' to set up your credentials"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please create it with your credentials."
    exit 1
fi

print_status "✓ Prerequisites validated successfully!"
echo ""

# Step 1: Set up secrets
print_header "📋 Step 1: Setting up AWS Secrets Manager"
print_status "Creating/updating secrets for Daily API and AWS credentials..."

if python3 setup-secrets.py; then
    print_status "✓ Secrets setup completed successfully!"
else
    print_error "Secrets setup failed"
    exit 1
fi
echo ""

# Step 2: Deploy infrastructure
print_header "🏗️  Step 2: Deploying Infrastructure"
print_status "Deploying CDK infrastructure (ECR, ECS, ALB, etc.)..."

cd infrastructure
chmod +x deploy.sh

if ./deploy.sh -e $ENVIRONMENT -r $AWS_REGION; then
    print_status "✓ Infrastructure deployment completed successfully!"
else
    print_error "Infrastructure deployment failed"
    exit 1
fi

cd ..
echo ""

# The infrastructure deployment script already handles image build and ECS service deployment
# So we're done at this point!

print_header "🎉 Deployment Complete!"
print_status "Your Pipecat Voice AI Agent has been successfully deployed to AWS ECS!"

# Get application URL
STACK_NAME="PipecatEcsStack-$ENVIRONMENT"
ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDnsName`].OutputValue' \
    --output text 2>/dev/null || echo "Not available")

if [ "$ALB_DNS" != "Not available" ]; then
    echo ""
    print_status "🌐 Application URL: http://$ALB_DNS"
    print_status "🔍 Health Check: http://$ALB_DNS/health"
    print_status "⚡ Ready Check: http://$ALB_DNS/ready"
fi

echo ""
print_status "📊 Monitoring Commands:"
print_status "  Service status: aws ecs describe-services --cluster pipecat-cluster-$ENVIRONMENT --services pipecat-service-$ENVIRONMENT --region $AWS_REGION"
print_status "  Application logs: aws logs tail /ecs/pipecat-voice-agent-$ENVIRONMENT/application --follow --region $AWS_REGION"
print_status "  Service events: aws ecs describe-services --cluster pipecat-cluster-$ENVIRONMENT --services pipecat-service-$ENVIRONMENT --region $AWS_REGION --query 'services[0].events[0:5]'"

echo ""
print_status "🧪 Testing your deployment:"
print_status "  1. Wait 2-3 minutes for the service to fully start"
print_status "  2. Test health endpoint: curl http://$ALB_DNS/health"
print_status "  3. Check ECS service status in AWS Console"
print_status "  4. Monitor CloudWatch logs for any issues"

print_header "✅ Deployment script completed successfully!"