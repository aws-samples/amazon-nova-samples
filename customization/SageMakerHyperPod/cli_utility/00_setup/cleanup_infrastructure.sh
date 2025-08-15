#!/usr/bin/env bash

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# 🧹 HyperPod EKS Infrastructure Cleanup Script
# 
# This script safely removes the HyperPod EKS infrastructure created by create_infrastructure.sh:
# - Deletes CloudFormation stack and all associated resources
# - Removes EKS cluster, VPC, subnets, and security groups
# - Cleans up IAM roles and compute instances
# - Removes local configuration files
#
# Prerequisites:
# - AWS CLI configured with appropriate permissions
# - .stack_arn file from the original deployment
#
# What this script does:
# 1. Validates stack existence and permissions
# 2. Shows resources that will be deleted
# 3. Initiates CloudFormation stack deletion
# 4. Monitors deletion progress
# 5. Cleans up local files

set -e

# Color codes for output
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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to prompt user for yes/no
prompt_yes_no() {
    while true; do
        read -p "$1 (y/n): " yn
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

echo "=========================================="
echo "🧹 HyperPod EKS Infrastructure Cleanup"
echo "=========================================="
echo
echo "This script will DELETE all AWS infrastructure created for your HyperPod cluster:"
echo "  • EKS cluster and all workloads"
echo "  • EC2 instances and Auto Scaling groups"
echo "  • VPC, subnets, and networking components"
echo "  • Security groups and IAM roles"
echo "  • Load balancers and storage volumes"
echo
print_warning "⚠️  THIS ACTION CANNOT BE UNDONE!"
print_warning "⚠️  ALL DATA AND WORKLOADS WILL BE PERMANENTLY LOST!"
echo

# Step 1: Validate prerequisites
print_step "Step 1: Validating Prerequisites"

# Check if AWS CLI is available
if ! command_exists aws; then
    print_error "AWS CLI not found. Please install AWS CLI first."
    exit 1
fi

print_status "AWS CLI found: $(aws --version)"

# Check if .stack_arn file exists
if [ ! -f .stack_arn ]; then
    print_error "Stack ARN file (.stack_arn) not found."
    print_error "This file is created by create_infrastructure.sh and contains the stack identifier."
    echo
    print_status "Alternative: You can manually specify the stack details"
    if prompt_yes_no "Do you want to manually enter stack information?"; then
        read -p "Enter CloudFormation stack name: " stack_name
        read -p "Enter AWS region: " region
        stack_identifier="$stack_name"
    else
        exit 1
    fi
else
    # Read stack ARN from file
    stack_arn=$(cat .stack_arn)
    print_status "Found stack ARN: $stack_arn"
    
    # Extract region and stack name from ARN
    region=$(echo "$stack_arn" | cut -d':' -f4)
    stack_name=$(echo "$stack_arn" | cut -d'/' -f2)
    stack_identifier="$stack_arn"
fi

print_status "Stack name: $stack_name"
print_status "Region: $region"

# Step 2: Validate stack exists
print_step "Step 2: Validating Stack Status"

print_status "Checking if stack exists and is accessible..."
if ! aws cloudformation describe-stacks --stack-name "$stack_identifier" --region "$region" >/dev/null 2>&1; then
    print_error "Cannot access stack '$stack_name' in region '$region'"
    print_error "Please check:"
    print_error "  • Stack name and region are correct"
    print_error "  • AWS credentials have proper permissions"
    print_error "  • Stack hasn't already been deleted"
    exit 1
fi

# Get stack status
stack_status=$(aws cloudformation describe-stacks \
    --stack-name "$stack_identifier" \
    --region "$region" \
    --query 'Stacks[0].StackStatus' \
    --output text)

print_status "Current stack status: $stack_status"

# Check if stack is in a deletable state
case $stack_status in
    DELETE_IN_PROGRESS)
        print_warning "Stack deletion is already in progress"
        if prompt_yes_no "Monitor the existing deletion process?"; then
            # Skip to monitoring step
            deletion_in_progress=true
        else
            exit 0
        fi
        ;;
    DELETE_COMPLETE)
        print_status "Stack has already been deleted"
        if prompt_yes_no "Clean up local files?"; then
            # Skip to cleanup step
            skip_deletion=true
        else
            exit 0
        fi
        ;;
    CREATE_IN_PROGRESS|UPDATE_IN_PROGRESS|UPDATE_ROLLBACK_IN_PROGRESS)
        print_error "Stack is currently being modified (status: $stack_status)"
        print_error "Please wait for the current operation to complete before deleting"
        exit 1
        ;;
esac

# Step 3: Show resources to be deleted
if [ "$skip_deletion" != "true" ] && [ "$deletion_in_progress" != "true" ]; then
    print_step "Step 3: Resources to be Deleted"
    
    print_status "Retrieving stack resources..."
    echo
    echo "The following AWS resources will be PERMANENTLY DELETED:"
    echo
    
    # List stack resources
    aws cloudformation list-stack-resources \
        --stack-name "$stack_identifier" \
        --region "$region" \
        --query 'StackResourceSummaries[*].[ResourceType,LogicalResourceId,PhysicalResourceId]' \
        --output table
    
    echo
    print_warning "💰 Deletion will stop all charges for these resources"
    print_warning "📊 Any data stored in EBS volumes or databases will be lost"
    print_warning "🔧 Running workloads and jobs will be terminated"
fi

# Step 4: Confirm deletion
if [ "$skip_deletion" != "true" ] && [ "$deletion_in_progress" != "true" ]; then
    print_step "Step 4: Deletion Confirmation"
    
    echo
    print_warning "⚠️  FINAL WARNING: This will permanently delete all infrastructure!"
    print_warning "⚠️  Make sure you have backed up any important data!"
    echo
    
    if ! prompt_yes_no "Are you absolutely sure you want to DELETE the entire HyperPod infrastructure?"; then
        print_status "Deletion cancelled by user"
        exit 0
    fi
    
    echo
    if ! prompt_yes_no "Type 'yes' to confirm - this is your last chance to cancel"; then
        print_status "Deletion cancelled by user"
        exit 0
    fi
fi

# Step 5: Delete stack
if [ "$skip_deletion" != "true" ] && [ "$deletion_in_progress" != "true" ]; then
    print_step "Step 5: Initiating Stack Deletion"
    
    print_status "Starting CloudFormation stack deletion..."
    aws cloudformation delete-stack \
        --stack-name "$stack_identifier" \
        --region "$region"
    
    print_status "Stack deletion initiated successfully"
fi

# Step 6: Monitor deletion
print_step "Step 6: Monitoring Deletion Progress"

print_status "Monitoring deletion progress (this may take 15-20 minutes)..."
print_status "You can also monitor progress in the AWS CloudFormation console"
echo

# Function to check stack status
check_stack_status() {
    aws cloudformation describe-stacks \
        --stack-name "$1" \
        --region "$2" \
        --query 'Stacks[0].StackStatus' \
        --output text 2>/dev/null || echo "DELETE_COMPLETE"
}

# Monitor deletion with progress updates
start_time=$(date +%s)
while true; do
    status=$(check_stack_status "$stack_identifier" "$region")
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))
    
    # Format elapsed time
    elapsed_minutes=$((elapsed_time / 60))
    elapsed_seconds=$((elapsed_time % 60))
    
    case $status in
        DELETE_COMPLETE)
            print_status "Stack deleted successfully after ${elapsed_minutes}m ${elapsed_seconds}s!"
            break
            ;;
        DELETE_IN_PROGRESS)
            echo -ne "\r\033[K${GREEN}[INFO]${NC} Stack deletion in progress... (${elapsed_minutes}m ${elapsed_seconds}s elapsed)"
            sleep 30
            ;;
        DELETE_FAILED)
            print_error "Stack deletion failed after ${elapsed_minutes}m ${elapsed_seconds}s"
            print_error "Some resources may need manual cleanup"
            print_error "Check the AWS CloudFormation console for error details"
            exit 1
            ;;
        *)
            print_error "Unexpected stack status: $status"
            exit 1
            ;;
    esac
done

# Step 7: Clean up local files
print_step "Step 7: Cleaning Up Local Files"

echo
print_status "Cleaning up local configuration files..."

files_to_clean=(
    ".stack_arn"
    "params.json"
    "og_cluster_config.json"
    "updated_cluster_config.json"
    "env_vars"
)

cleaned_files=()
for file in "${files_to_clean[@]}"; do
    if [ -f "$file" ]; then
        rm -f "$file"
        cleaned_files+=("$file")
    fi
done

if [ ${#cleaned_files[@]} -gt 0 ]; then
    print_status "Removed local files:"
    for file in "${cleaned_files[@]}"; do
        echo "  • $file"
    done
else
    print_status "No local files found to clean up"
fi

# Final completion message
echo
print_status "=========================================="
print_status "✅ Infrastructure cleanup completed!"
print_status "=========================================="
echo
print_status "What was deleted:"
echo "  • CloudFormation stack and all resources"
echo "  • EKS cluster and compute instances"
echo "  • VPC, subnets, and networking components"
echo "  • IAM roles and security groups"
echo "  • Local configuration files"
echo
print_status "💰 All AWS charges for these resources have stopped"
print_status "🔄 You can run create_infrastructure.sh again to recreate the infrastructure"
echo
print_warning "Note: If you had any persistent data (EFS, databases), verify it was backed up"