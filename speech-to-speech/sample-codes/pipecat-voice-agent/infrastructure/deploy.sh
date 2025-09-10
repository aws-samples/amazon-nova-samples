#!/bin/bash

# Pipecat ECS Infrastructure Deployment Script

set -e

# Default values
ENVIRONMENT="test"
USE_DEFAULT_VPC="true"
AWS_REGION="eu-north-1"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --custom-vpc)
      USE_DEFAULT_VPC="false"
      shift
      ;;
    -r|--region)
      AWS_REGION="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  -e, --environment ENV    Set environment (default: test)"
      echo "  --custom-vpc            Use custom VPC instead of default"
      echo "  -r, --region REGION     Set AWS region (default: eu-north-1)"
      echo "  -h, --help              Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

echo "Deploying Pipecat ECS Infrastructure..."
echo "Environment: $ENVIRONMENT"
echo "Use Default VPC: $USE_DEFAULT_VPC"
echo "AWS Region: $AWS_REGION"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Error: AWS CLI is not configured or credentials are invalid"
    echo "Please run 'aws configure' to set up your credentials"
    exit 1
fi

# Check if CDK is bootstrapped
echo "Checking CDK bootstrap status..."
if ! aws cloudformation describe-stacks --stack-name CDKToolkit --region $AWS_REGION > /dev/null 2>&1; then
    echo "CDK is not bootstrapped in region $AWS_REGION"
    echo "Running CDK bootstrap..."
    npx cdk bootstrap --region $AWS_REGION
fi

# Install dependencies
echo "Installing dependencies..."
npm install

# Build the project
echo "Building CDK project..."
npm run build

# Deploy the stack
echo "Deploying CDK stack..."
npx cdk deploy \
  --context environment=$ENVIRONMENT \
  --context useDefaultVpc=$USE_DEFAULT_VPC \
  --region $AWS_REGION \
  --require-approval never

echo "Infrastructure deployment completed successfully!"
echo ""

# Get ECR repository URI from stack outputs
STACK_NAME="PipecatEcsStack-$ENVIRONMENT"
REPOSITORY_URI=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`RepositoryUri`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ -n "$REPOSITORY_URI" ]; then
    echo "ECR Repository created: $REPOSITORY_URI"
    
    # Build and push initial Docker image
    echo ""
    echo "Building and pushing initial Docker image..."
    
    # Go back to parent directory to access Dockerfile and build scripts
    cd ..
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo "Warning: Docker is not running. Skipping image build."
        echo "Please start Docker and run: ./scripts/build-and-push.sh -e $ENVIRONMENT -r $AWS_REGION"
    else
        # Make build script executable and run it
        chmod +x scripts/build-and-push.sh
        
        # Build and push the image
        if ./scripts/build-and-push.sh -e $ENVIRONMENT -r $AWS_REGION -t latest --force; then
            echo "✓ Docker image built and pushed successfully!"
            
            # Update ECS service with the new image
            echo ""
            echo "Updating ECS service with new image..."
            chmod +x scripts/deploy-service.sh
            
            if ./scripts/deploy-service.sh -e $ENVIRONMENT -r $AWS_REGION -t latest --update; then
                echo "✓ ECS service updated successfully!"
                
                # Get application URL
                ALB_DNS=$(aws cloudformation describe-stacks \
                    --stack-name $STACK_NAME \
                    --region $AWS_REGION \
                    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDnsName`].OutputValue' \
                    --output text 2>/dev/null || echo "Not available")
                
                echo ""
                echo "🎉 Complete deployment finished!"
                if [ "$ALB_DNS" != "Not available" ]; then
                    echo "🌐 Application URL: http://$ALB_DNS"
fi
                echo "📋 Monitor your application:"
                echo "  - Service status: aws ecs describe-services --cluster pipecat-cluster-$ENVIRONMENT --services pipecat-service-$ENVIRONMENT --region $AWS_REGION"
                echo "  - Application logs: aws logs tail /ecs/pipecat-voice-agent-$ENVIRONMENT/application --follow --region $AWS_REGION"
            else
                echo "⚠️  ECS service update failed. You may need to run it manually:"
                echo "   ./scripts/deploy-service.sh -e $ENVIRONMENT -r $AWS_REGION -t latest --update"
            fi
        else
            echo "⚠️  Docker image build failed. You may need to run it manually:"
            echo "   ./scripts/build-and-push.sh -e $ENVIRONMENT -r $AWS_REGION -t latest"
        fi
    fi
else
    echo "⚠️  Could not retrieve ECR repository URI from stack outputs"
fi

echo ""
echo "Next steps:"
echo "1. Set up secrets in AWS Secrets Manager (if not done already):"
echo "   python3 setup-secrets.py"
echo "2. Test the application at the URL above"
echo "3. Monitor the deployment and logs"