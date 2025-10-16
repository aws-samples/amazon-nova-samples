#!/bin/bash
set -e

echo "ACBT QA Testing App - CloudFormation Stack Update Script"
echo "========================================================"
echo "This script will update the existing CloudFormation stack with the new template changes."
echo "It includes security fixes and Checkov skip annotations."
echo ""

# Default stack name
STACK_NAME="acbt-qa-testing"

# Function to check if stack exists
check_stack_exists() {
    aws cloudformation describe-stacks --stack-name "$1" &> /dev/null
}

# Function to get stack status
get_stack_status() {
    aws cloudformation describe-stacks --stack-name "$1" --query 'Stacks[0].StackStatus' --output text
}

# Get current stack name if it exists with different naming
echo "Searching for existing ACBT QA Testing stacks..."
EXISTING_STACKS=$(aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE --query "StackSummaries[?contains(StackName,'acbt-qa-testing') || contains(StackName,'acbt')].StackName" --output text)

if [ -n "$EXISTING_STACKS" ]; then
    echo "Found existing stacks:"
    echo "$EXISTING_STACKS"
    echo ""
    echo "Please enter the stack name you want to update (or press Enter for default: $STACK_NAME):"
    read -r USER_STACK_NAME
    if [ -n "$USER_STACK_NAME" ]; then
        STACK_NAME="$USER_STACK_NAME"
    fi
else
    echo "No existing stacks found. Please enter the stack name to update:"
    read -r USER_STACK_NAME
    if [ -n "$USER_STACK_NAME" ]; then
        STACK_NAME="$USER_STACK_NAME"
    fi
fi

# Verify stack exists
if ! check_stack_exists "$STACK_NAME"; then
    echo "Error: Stack '$STACK_NAME' does not exist."
    echo "Available stacks:"
    aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE --query "StackSummaries[].StackName" --output table
    exit 1
fi

# Check current stack status
CURRENT_STATUS=$(get_stack_status "$STACK_NAME")
echo "Current stack status: $CURRENT_STATUS"

if [[ "$CURRENT_STATUS" == *"IN_PROGRESS"* ]]; then
    echo "Error: Stack is currently in progress. Please wait for the current operation to complete."
    exit 1
fi

# Get current stack parameters
echo "Retrieving current stack parameters..."
CURRENT_PARAMS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].Parameters')
echo "Current parameters:"
echo "$CURRENT_PARAMS" | jq -r '.[] | "\(.ParameterKey)=\(.ParameterValue)"'

# Validate the template
echo ""
echo "Validating CloudFormation template..."
aws cloudformation validate-template --template-body file://cloudformation-simple.yaml > /dev/null
echo "Template validation successful!"

# Show what will be updated
echo ""
echo "Generating change set to preview changes..."
CHANGE_SET_NAME="update-$(date +%s)"

# Convert parameters to the correct format for change set
PARAM_OVERRIDES=$(echo "$CURRENT_PARAMS" | jq -r '.[] | "ParameterKey=\(.ParameterKey),UsePreviousValue=true"' | tr '\n' ' ')

aws cloudformation create-change-set \
    --stack-name "$STACK_NAME" \
    --template-body file://cloudformation-simple.yaml \
    --change-set-name "$CHANGE_SET_NAME" \
    --parameters $PARAM_OVERRIDES

echo "Waiting for change set creation..."
aws cloudformation wait change-set-create-complete \
    --stack-name "$STACK_NAME" \
    --change-set-name "$CHANGE_SET_NAME"

# Display changes
echo ""
echo "Proposed changes:"
aws cloudformation describe-change-set \
    --stack-name "$STACK_NAME" \
    --change-set-name "$CHANGE_SET_NAME" \
    --query 'Changes[].{Action:Action,Resource:ResourceChange.LogicalResourceId,Type:ResourceChange.ResourceType,Replacement:ResourceChange.Replacement}' \
    --output table

# Ask for confirmation
echo ""
echo "Do you want to proceed with these changes? (y/N):"
read -r CONFIRM

if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Cancelling update. Cleaning up change set..."
    aws cloudformation delete-change-set \
        --stack-name "$STACK_NAME" \
        --change-set-name "$CHANGE_SET_NAME"
    echo "Update cancelled."
    exit 0
fi

# Execute the change set
echo "Executing stack update..."
aws cloudformation execute-change-set \
    --stack-name "$STACK_NAME" \
    --change-set-name "$CHANGE_SET_NAME"

echo "Waiting for stack update to complete..."
echo "This may take several minutes..."

# Monitor the update progress
aws cloudformation wait stack-update-complete --stack-name "$STACK_NAME"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Stack update completed successfully!"
    
    # Get updated deployment information
    echo ""
    echo "Updated deployment information:"
    STACK_OUTPUT=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs')

    # Extract values from stack output with better error handling
    BUCKET_NAME=$(echo "$STACK_OUTPUT" | jq -r '.[] | select(.OutputKey=="S3BucketName").OutputValue // "Unknown"')
    
    # Try to get CloudFront Distribution ID, handling the conditional output
    DISTRIBUTION_ID=$(echo "$STACK_OUTPUT" | jq -r '.[] | select(.OutputKey=="CloudFrontDistributionID").OutputValue // empty' | head -1)
    if [ -z "$DISTRIBUTION_ID" ] || [ "$DISTRIBUTION_ID" = "null" ]; then
        DISTRIBUTION_ID="N/A"
    fi
    
    WEBSITE_URL=$(echo "$STACK_OUTPUT" | jq -r '.[] | select(.OutputKey=="WebsiteURL").OutputValue // "Unknown"')

    echo "S3 Bucket: $BUCKET_NAME"
    echo "CloudFront Distribution ID: $DISTRIBUTION_ID"
    echo "Website URL: $WEBSITE_URL"

    # Debug: Show all stack outputs for troubleshooting
    echo ""
    echo "Debug - All stack outputs:"
    echo "$STACK_OUTPUT" | jq -r '.[] | "\(.OutputKey): \(.OutputValue)"'

    # Ask if user wants to invalidate CloudFront cache
    if [ "$DISTRIBUTION_ID" != "N/A" ] && [ "$DISTRIBUTION_ID" != "Unknown" ] && [ -n "$DISTRIBUTION_ID" ]; then
        echo ""
        echo "Do you want to invalidate the CloudFront cache to ensure changes are visible? (y/N):"
        read -r INVALIDATE
        
        if [[ "$INVALIDATE" == "y" || "$INVALIDATE" == "Y" ]]; then
            echo "Creating CloudFront invalidation..."
            INVALIDATION_ID=$(aws cloudfront create-invalidation \
                --distribution-id "$DISTRIBUTION_ID" \
                --paths "/*" \
                --query 'Invalidation.Id' \
                --output text)
            echo "Invalidation created with ID: $INVALIDATION_ID"
            echo "Cache invalidation may take 10-15 minutes to complete."
        fi
    fi

    echo ""
    echo "🎉 Stack update completed successfully!"
    echo "Your updated application is available at: $WEBSITE_URL"
    
else
    echo ""
    echo "❌ Stack update failed!"
    echo "Check the CloudFormation console for detailed error information."
    echo "The stack may have been rolled back to its previous state."
    exit 1
fi
