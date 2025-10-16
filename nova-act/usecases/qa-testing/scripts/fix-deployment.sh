#!/bin/bash
set -e

echo "ACBT QA Testing App Deployment Fix Script"
echo "----------------------------------------"
echo "This script will fix the CloudFront access denied issue by:"
echo "1. Deleting the current CloudFormation stack"
echo "2. Deploying a new stack with the fixed template"
echo "3. Uploading all web files to the S3 bucket"
echo ""
echo "Press Enter to continue or Ctrl+C to cancel..."
read -r

# Default stack name
STACK_NAME="acbt-qa-testing"

# Get current stack name if it exists
CURRENT_STACK=$(aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query "StackSummaries[?contains(StackName,'acbt-qa-testing')].StackName" --output text)
if [ -n "$CURRENT_STACK" ]; then
  STACK_NAME=$CURRENT_STACK
  echo "Found existing stack: $STACK_NAME"
fi

# Generate a unique bucket name
BUCKET_NAME="acbt-qa-testing-$(date +%s)"
echo "Will create a new bucket: $BUCKET_NAME"

# Delete the existing stack if it exists
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" &> /dev/null; then
  echo "Deleting existing stack: $STACK_NAME..."
  aws cloudformation delete-stack --stack-name "$STACK_NAME"

  echo "Waiting for stack deletion to complete..."
  aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME"
  echo "Stack deleted successfully."
fi

# Create new CloudFormation stack
echo "Creating CloudFormation stack: $STACK_NAME with bucket: $BUCKET_NAME..."
aws cloudformation create-stack \
  --stack-name "$STACK_NAME" \
  --template-body file://cloudformation-simple.yaml \
  --parameters ParameterKey=BucketName,ParameterValue="$BUCKET_NAME"

echo "Waiting for stack creation to complete..."
aws cloudformation wait stack-create-complete --stack-name "$STACK_NAME"
echo "Stack created successfully!"

# Get deployment information
echo "Retrieving deployment information..."
STACK_OUTPUT=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs')

# Extract values from stack output
BUCKET_NAME=$(echo "$STACK_OUTPUT" | jq -r '.[] | select(.OutputKey=="S3BucketName").OutputValue')
DISTRIBUTION_ID=$(echo "$STACK_OUTPUT" | jq -r '.[] | select(.OutputKey=="CloudFrontDistributionID").OutputValue')
WEBSITE_URL=$(echo "$STACK_OUTPUT" | jq -r '.[] | select(.OutputKey=="WebsiteURL").OutputValue')

echo "S3 Bucket: $BUCKET_NAME"
echo "CloudFront Distribution ID: $DISTRIBUTION_ID"
echo "Website URL: $WEBSITE_URL"

# Deploy files to S3
echo "Uploading files to S3..."
aws s3 sync . "s3://$BUCKET_NAME/" \
  --exclude "*.md" \
  --exclude "cloudformation*.yaml" \
  --exclude "node_modules/*" \
  --exclude "package*.json" \
  --exclude "*.sh" \
  --exclude ".git/*" \
  --exclude "deploy.sh"

# Create CloudFront invalidation if CloudFront is enabled
if [ "$DISTRIBUTION_ID" != "N/A" ]; then
  echo "Creating CloudFront invalidation..."
  aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths "/*"
  echo "Invalidation created successfully."
fi

# Print success message
echo ""
echo "Deployment fixed successfully!"
echo "Your application is available at: $WEBSITE_URL"
echo ""
echo "Please allow a few minutes for CloudFront to fully deploy."