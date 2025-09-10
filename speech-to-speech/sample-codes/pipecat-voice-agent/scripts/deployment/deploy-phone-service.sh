#!/bin/bash

# Phone Service Deployment Script for Pipecat ECS
# This script deploys the phone service with Twilio integration

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
    echo -e "${BLUE}[PHONE-DEPLOY]${NC} $1"
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
      echo "This script deploys the Pipecat Phone Service with Twilio integration:"
      echo "1. Build and push phone service Docker image to ECR"
      echo "2. Update phone service ECS service with new image"
      echo "3. Display Twilio webhook URL for configuration"
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
      echo "  $0                                    # Full phone service deployment"
      echo "  $0 -e prod -t v1.2.3                # Deploy to prod with specific tag"
      echo "  $0 --build-only                     # Only build and push phone image"
      echo "  $0 --deploy-only -t v1.2.3          # Only deploy existing phone image"
      echo ""
      echo "Prerequisites:"
      echo "  - AWS CLI configured with appropriate credentials"
      echo "  - Docker installed and running"
      echo "  - Infrastructure deployed with phone service support"
      echo "  - Twilio credentials configured in AWS Secrets Manager"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

print_header "Starting Pipecat Phone Service Deployment"
print_status "Environment: $ENVIRONMENT"
print_status "AWS Region: $AWS_REGION"
print_status "Image Tag: $IMAGE_TAG"
print_status "Skip Build: $SKIP_BUILD"
print_status "Skip Deploy: $SKIP_DEPLOY"

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
    print_error "Please deploy the infrastructure first with phone service support"
    exit 1
fi

# Check if phone service exists in the stack
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

print_status "Prerequisites validated successfully!"

# Step 1: Build and push phone service Docker image
if [ "$SKIP_BUILD" = "false" ]; then
    print_header "Step 1: Building and pushing phone service Docker image"
    
    # Get ECR repository URI
    PHONE_REPO_URI=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $AWS_REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`PhoneRepositoryUri`].OutputValue' \
        --output text)
    
    if [ -z "$PHONE_REPO_URI" ]; then
        print_error "Failed to get phone repository URI from CloudFormation"
        exit 1
    fi
    
    print_status "Phone Repository URI: $PHONE_REPO_URI"
    
    # Login to ECR
    print_status "Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $PHONE_REPO_URI
    
    # Build the phone service image
    print_status "Building phone service Docker image..."
    docker build -f docker/Dockerfile.phone -t pipecat-phone-service:$IMAGE_TAG .
    
    # Tag for ECR
    docker tag pipecat-phone-service:$IMAGE_TAG $PHONE_REPO_URI:$IMAGE_TAG
    
    # Check if image already exists (unless force build)
    if [ "$FORCE_BUILD" = "false" ]; then
        if aws ecr describe-images --repository-name $(basename $PHONE_REPO_URI) --image-ids imageTag=$IMAGE_TAG --region $AWS_REGION > /dev/null 2>&1; then
            print_warning "Image with tag '$IMAGE_TAG' already exists in ECR"
            print_status "Use --force-build to rebuild anyway"
        fi
    fi
    
    # Push to ECR
    print_status "Pushing phone service image to ECR..."
    docker push $PHONE_REPO_URI:$IMAGE_TAG
    
    print_status "Phone service build and push completed successfully!"
else
    print_warning "Skipping build step as requested"
fi

# Step 2: Deploy phone service to ECS
if [ "$SKIP_DEPLOY" = "false" ]; then
    print_header "Step 2: Deploying phone service to ECS"
    
    # Get service details
    PHONE_SERVICE_NAME=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $AWS_REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`PhoneServiceName`].OutputValue' \
        --output text)
    
    CLUSTER_NAME=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $AWS_REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`ClusterName`].OutputValue' \
        --output text)
    
    if [ -z "$PHONE_SERVICE_NAME" ] || [ -z "$CLUSTER_NAME" ]; then
        print_error "Failed to get phone service or cluster name from CloudFormation"
        exit 1
    fi
    
    print_status "Phone Service: $PHONE_SERVICE_NAME"
    print_status "Cluster: $CLUSTER_NAME"
    
    # Update the service to use the new image
    print_status "Updating phone service with new image..."
    
    # Get current task definition
    CURRENT_TASK_DEF=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $PHONE_SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].taskDefinition' \
        --output text)
    
    if [ -z "$CURRENT_TASK_DEF" ]; then
        print_error "Failed to get current task definition"
        exit 1
    fi
    
    # Get the task definition family name
    TASK_DEF_FAMILY=$(echo $CURRENT_TASK_DEF | cut -d':' -f6 | cut -d'/' -f2)
    
    # Create new task definition revision with updated image
    print_status "Creating new task definition revision..."
    
    # Get current task definition JSON
    TASK_DEF_JSON=$(aws ecs describe-task-definition \
        --task-definition $CURRENT_TASK_DEF \
        --region $AWS_REGION \
        --query 'taskDefinition')
    
    # Update the image in the task definition
    NEW_TASK_DEF=$(echo $TASK_DEF_JSON | jq --arg image "$PHONE_REPO_URI:$IMAGE_TAG" \
        '.containerDefinitions[0].image = $image | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)')
    
    # Register new task definition
    NEW_TASK_DEF_ARN=$(echo $NEW_TASK_DEF | aws ecs register-task-definition \
        --region $AWS_REGION \
        --cli-input-json file:///dev/stdin \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)
    
    if [ -z "$NEW_TASK_DEF_ARN" ]; then
        print_error "Failed to register new task definition"
        exit 1
    fi
    
    print_status "New task definition: $NEW_TASK_DEF_ARN"
    
    # Update the service
    print_status "Updating phone service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $PHONE_SERVICE_NAME \
        --task-definition $NEW_TASK_DEF_ARN \
        --region $AWS_REGION > /dev/null
    
    # Wait for deployment to complete
    print_status "Waiting for phone service deployment to complete..."
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $PHONE_SERVICE_NAME \
        --region $AWS_REGION
    
    print_status "Phone service deployment completed successfully!"
else
    print_warning "Skipping deployment step as requested"
fi

# Final status and Twilio configuration
print_header "Phone Service Deployment Complete!"

if [ "$SKIP_BUILD" = "false" ] && [ "$SKIP_DEPLOY" = "false" ]; then
    print_status "Full phone service deployment completed successfully!"
elif [ "$SKIP_BUILD" = "true" ]; then
    print_status "Phone service deployment completed (build skipped)"
elif [ "$SKIP_DEPLOY" = "true" ]; then
    print_status "Phone service build completed (deployment skipped)"
fi

# Get phone service URL for Twilio configuration
PHONE_ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`PhoneLoadBalancerDnsName`].OutputValue' \
    --output text 2>/dev/null || echo "Not available")

TWILIO_WEBHOOK_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`TwilioWebhookUrl`].OutputValue' \
    --output text 2>/dev/null || echo "Not available")

if [ "$PHONE_ALB_DNS" != "Not available" ]; then
    print_header "🔗 Twilio Configuration Required"
    print_status "📞 Phone Service URL: http://$PHONE_ALB_DNS"
    print_status "🎯 Twilio Webhook URL: $TWILIO_WEBHOOK_URL"
    print_status ""
    print_status "📋 Manual Twilio Configuration Steps:"
    print_status "  1. Log in to your Twilio Console (https://console.twilio.com/)"
    print_status "  2. Go to Phone Numbers > Manage > Active numbers"
    print_status "  3. Click on your Twilio phone number"
    print_status "  4. In the 'Voice Configuration' section:"
    print_status "     - Set 'A call comes in' webhook to: $TWILIO_WEBHOOK_URL"
    print_status "     - Set HTTP method to: POST"
    print_status "  5. Click 'Save configuration'"
    print_status ""
    print_status "🧪 Testing:"
    print_status "  - Health check: curl http://$PHONE_ALB_DNS/health"
    print_status "  - Call your Twilio number to test the integration"
fi

print_status "📋 Next steps:"
print_status "  1. Configure Twilio webhook URL as shown above"
print_status "  2. Test phone calls to your Twilio number"
print_status "  3. Monitor logs: aws logs tail /ecs/pipecat-phone-service-$ENVIRONMENT --follow --region $AWS_REGION"
print_status "  4. Check service status: aws ecs describe-services --cluster $CLUSTER_NAME --services $PHONE_SERVICE_NAME --region $AWS_REGION"

print_header "Phone service deployment script completed!"