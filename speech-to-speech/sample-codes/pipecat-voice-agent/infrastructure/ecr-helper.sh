#!/bin/bash

# ECR Helper Script for Pipecat ECS Deployment

set -e

# Default values
ENVIRONMENT="test"
AWS_REGION="eu-north-1"
ACTION=""

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
    --login)
      ACTION="login"
      shift
      ;;
    --get-uri)
      ACTION="get-uri"
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS] ACTION"
      echo "Actions:"
      echo "  --login                 Login to ECR"
      echo "  --get-uri              Get ECR repository URI"
      echo "Options:"
      echo "  -e, --environment ENV   Set environment (default: test)"
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

if [ -z "$ACTION" ]; then
    echo "Error: No action specified. Use --help for usage information."
    exit 1
fi

REPOSITORY_NAME="pipecat-voice-agent-$ENVIRONMENT"

case $ACTION in
    "login")
        echo "Logging into ECR..."
        aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com
        echo "ECR login successful!"
        ;;
    "get-uri")
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        REPOSITORY_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPOSITORY_NAME"
        echo $REPOSITORY_URI
        ;;
esac