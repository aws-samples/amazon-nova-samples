#!/bin/bash

# Deploy service script for updating ECS service

set -e

# Default values
ENVIRONMENT="test"
AWS_REGION="eu-north-1"
IMAGE_TAG="latest"
UPDATE_SERVICE=false

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
    --update)
      UPDATE_SERVICE=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  -e, --environment ENV    Set environment (default: test)"
      echo "  -r, --region REGION     Set AWS region (default: eu-north-1)"
      echo "  -t, --tag TAG           Set image tag (default: latest)"
      echo "  --update                Update ECS service"
      echo "  -h, --help              Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

CLUSTER_NAME="pipecat-cluster-$ENVIRONMENT"
SERVICE_NAME="pipecat-service-$ENVIRONMENT"
REPO_URI="094271239310.dkr.ecr.$AWS_REGION.amazonaws.com/pipecat-voice-agent-$ENVIRONMENT"

echo "🚀 Deploying ECS service update"
echo "Cluster: $CLUSTER_NAME"
echo "Service: $SERVICE_NAME"
echo "Image: $REPO_URI:$IMAGE_TAG"
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"

if [ "$UPDATE_SERVICE" = true ]; then
    echo "🔄 Forcing service update..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --force-new-deployment \
        --region $AWS_REGION
    
    echo "✅ Service update initiated!"
    echo ""
    echo "Monitor deployment status:"
    echo "  aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION"
    echo ""
    echo "View service logs:"
    echo "  aws logs tail /ecs/pipecat-voice-agent-$ENVIRONMENT/application --follow --region $AWS_REGION"
else
    echo "ℹ️  Use --update flag to actually update the service"
fi