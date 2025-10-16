#!/bin/bash
set -e

echo "CloudFront Cache Invalidation Script"
echo "===================================="
echo ""

# Default stack name
STACK_NAME="acbt-qa-testing"

# Function to check if stack exists
check_stack_exists() {
    aws cloudformation describe-stacks --stack-name "$1" &> /dev/null
}

# Get stack name from user or use default
echo "Enter the CloudFormation stack name (or press Enter for default: $STACK_NAME):"
read -r USER_STACK_NAME
if [ -n "$USER_STACK_NAME" ]; then
    STACK_NAME="$USER_STACK_NAME"
fi

# Verify stack exists
if ! check_stack_exists "$STACK_NAME"; then
    echo "Error: Stack '$STACK_NAME' does not exist."
    echo ""
    echo "Available stacks:"
    aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE --query "StackSummaries[].StackName" --output table
    exit 1
fi

echo "Getting CloudFront distribution information from stack: $STACK_NAME"

# Get stack outputs
STACK_OUTPUT=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs')

echo ""
echo "Stack outputs:"
echo "$STACK_OUTPUT" | jq -r '.[] | "\(.OutputKey): \(.OutputValue)"'

# Extract CloudFront Distribution ID
DISTRIBUTION_ID=$(echo "$STACK_OUTPUT" | jq -r '.[] | select(.OutputKey=="CloudFrontDistributionID").OutputValue // empty')

if [ -z "$DISTRIBUTION_ID" ] || [ "$DISTRIBUTION_ID" = "null" ] || [ "$DISTRIBUTION_ID" = "N/A" ]; then
    echo ""
    echo "❌ No CloudFront distribution found in this stack."
    echo "This stack may not have CloudFront enabled or the distribution output is not available."
    
    # Check if CreateCloudFront parameter is false
    CREATE_CF=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Parameters[?ParameterKey==`CreateCloudFront`].ParameterValue' \
        --output text)
    
    if [ "$CREATE_CF" = "false" ]; then
        echo "The CreateCloudFront parameter is set to 'false' for this stack."
    fi
    exit 1
fi

echo ""
echo "Found CloudFront Distribution ID: $DISTRIBUTION_ID"

# Verify the distribution exists
echo "Verifying distribution exists..."
if ! aws cloudfront get-distribution --id "$DISTRIBUTION_ID" &> /dev/null; then
    echo "❌ Error: CloudFront distribution '$DISTRIBUTION_ID' does not exist or is not accessible."
    echo "Please check your AWS credentials and permissions."
    exit 1
fi

echo "✅ Distribution verified successfully."

# Ask for confirmation
echo ""
echo "This will invalidate ALL files (/*) in the CloudFront distribution."
echo "Invalidation may take 10-15 minutes to complete and may incur charges."
echo ""
echo "Do you want to proceed? (y/N):"
read -r CONFIRM

if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Invalidation cancelled."
    exit 0
fi

# Create invalidation
echo ""
echo "Creating CloudFront invalidation..."
INVALIDATION_OUTPUT=$(aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths "/*")

INVALIDATION_ID=$(echo "$INVALIDATION_OUTPUT" | jq -r '.Invalidation.Id')
INVALIDATION_STATUS=$(echo "$INVALIDATION_OUTPUT" | jq -r '.Invalidation.Status')

echo "✅ Invalidation created successfully!"
echo ""
echo "Invalidation Details:"
echo "- ID: $INVALIDATION_ID"
echo "- Status: $INVALIDATION_STATUS"
echo "- Distribution: $DISTRIBUTION_ID"
echo "- Paths: /*"

echo ""
echo "🕐 The invalidation is now in progress..."
echo "You can check the status with:"
echo "aws cloudfront get-invalidation --distribution-id $DISTRIBUTION_ID --id $INVALIDATION_ID"

echo ""
echo "Or monitor it in the AWS Console:"
echo "https://console.aws.amazon.com/cloudfront/v3/home#/distributions/$DISTRIBUTION_ID"

echo ""
echo "✨ Invalidation request completed successfully!"
echo "Cache invalidation typically takes 10-15 minutes to complete."
