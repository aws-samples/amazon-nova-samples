#!/usr/bin/env bash

# CloudFormation Stack Creation Script for HyperPod EKS
# This script handles the initial setup and CloudFormation stack creation

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

# Function to prompt for input with default value
prompt_input() {
    local prompt="$1"
    local default="$2"
    local input
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        echo "${input:-$default}"
    else
        read -p "$prompt: " input
        echo "$input"
    fi
}

echo "=========================================="
echo "HyperPod EKS CloudFormation Stack Creation"
echo "=========================================="
echo

# Check if we have sudo access
if ! sudo -v >/dev/null 2>&1; then
    print_error "This script requires sudo access for installing packages. Please run with sudo privileges."
    exit 1
fi

# Step 0: Installations
print_step "Step 0: Checking and Installing Required Tools"

# 0.0 Install jq
print_status "Checking jq installation..."
if ! command_exists jq; then
    print_warning "jq not found. Installing..."
    if prompt_yes_no "Do you want to install jq?"; then
        if [ "$(uname)" == "Darwin" ]; then
            brew install jq
        else
            sudo apt-get update && sudo apt-get install -y jq
        fi
        print_status "jq installed successfully"
    else
        print_error "jq is required for JSON processing. Exiting."
        exit 1
    fi
else
    print_status "jq is already installed: $(jq --version)"
fi

# 0.1 Install AWS CLI
print_status "Checking AWS CLI installation..."
if ! command_exists aws; then
    print_warning "AWS CLI not found. Installing..."
    if prompt_yes_no "Do you want to install AWS CLI?"; then
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install --update
        rm -rf awscliv2.zip aws/
        print_status "AWS CLI installed successfully"
    else
        print_error "AWS CLI is required. Exiting."
        exit 1
    fi
else
    print_status "AWS CLI is already installed: $(aws --version)"
fi

echo
print_step "Step 1: Configuration Parameters"

# Initialize parameter arrays
param_keys=(
    "CreateEKSClusterStack"
    "EKSClusterName"
    # "CreateVPCStack"
    # "VpcId"
    # "NatGatewayId"
    "NodeRecovery"
    "HyperPodClusterName"
    "ResourceNamePrefix"
    "AvailabilityZoneId"
    # "AcceleratedThreadsPerCore"
    # "AcceleratedLifeCycleConfigOnCreate"
    # "AcceleratedInstanceGroupName"
    # "EnableInstanceStressCheck"
    "AcceleratedInstanceType"
    "AcceleratedInstanceCount"
    "CreateGeneralPurposeInstanceGroup"
)

param_defaults=(
    "true"
    "my-eks-cluster"
    # "sg-1234567890abcdef0"
    # "true"
    # "vpc-1234567890abcdef0"
    # "nat-1234567890abcdef0"
    "None"
    "hp-cluster"
    "hp-eks-test"
    "use1-az2"
    # "1"
    # "on_create.sh"
    # "accelerated-worker-group-1"
    # "true"
    "ml.g5.8xlarge"
    "1"
    "false"
)

param_descriptions=(
    "Create new EKS cluster stack"
    "Name of the EKS cluster"
    # "Security Group ID for the cluster"
    # "Create new VPC stack"
    # "VPC ID to use"
    # "NAT Gateway ID"
    "NAT Recovery"
    "HyperPod cluster name"
    "Prefix for resource names"
    "Availability Zone ID"
    # "AcceleratedThreadsPerCore"
    # "AcceleratedLifeCycleConfigOnCreate"
    # "AcceleratedInstanceGroupName"
    # "EnableInstanceStressCheck"
    "Instance type for accelerated instances"
    "Number of accelerated instances"
    "Create general purpose instance group"
)

print_status "Please review and configure the following parameters:"
echo

# Create a temporary file to store parameters
temp_params_file=$(mktemp)

# Write opening bracket
echo "[" > "$temp_params_file"

# Collect user input for parameters
first=true
for i in "${!param_keys[@]}"; do
    echo -e "${BLUE}${param_descriptions[$i]}${NC}"
    value=$(prompt_input "  ${param_keys[$i]}" "${param_defaults[$i]}")
    
    # Add comma for all but first entry
    if [ "$first" = true ]; then
        first=false
    else
        echo "," >> "$temp_params_file"
    fi
    
    # Add parameter entry
    jq -n \
        --arg key "${param_keys[$i]}" \
        --arg value "$value" \
        '{"ParameterKey": $key, "ParameterValue": $value}' >> "$temp_params_file"
done

# Write closing bracket
echo "]" >> "$temp_params_file"

# Step 2: Create params.json
print_step "Step 2: Creating params.json file"

# Format and save the final JSON
jq '.' "$temp_params_file" > params.json

# Clean up temp file
rm "$temp_params_file"

print_status "Created params.json file:"
cat params.json
echo

if ! prompt_yes_no "Do the parameters look correct?"; then
    print_error "Please edit params.json manually and re-run the script."
    exit 1
fi

# Step 3: Download and run CloudFormation stack
print_step "Step 3: Downloading CloudFormation template and creating stack"

print_status "Downloading main-stack.yaml..."
curl -O https://raw.githubusercontent.com/aws-samples/awsome-distributed-training/refs/heads/main/1.architectures/7.sagemaker-hyperpod-eks/cfn-templates/nested-stacks/main-stack.yaml

stack_name=$(prompt_input "Enter stack name" "hp-eks-test-stack")
region=$(prompt_input "Enter AWS region" "us-east-1")

print_status "Creating CloudFormation stack: $stack_name"
if prompt_yes_no "Proceed with stack creation?"; then
    # Create the stack and capture the stack ARN
    stack_arn=$(aws cloudformation create-stack \
        --stack-name "$stack_name" \
        --template-body file://main-stack.yaml \
        --region "$region" \
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
        --parameters file://params.json \
        --query 'StackId' \
        --output text)
    
    print_status "Stack creation initiated with ARN: $stack_arn"
    print_status "Waiting for stack to complete (this may take 20-30 minutes)..."
    
    # Function to check stack status
    check_stack_status() {
        aws cloudformation describe-stacks \
            --stack-name "$1" \
            --region "$2" \
            --query 'Stacks[0].StackStatus' \
            --output text
    }
    
    # Monitor stack creation with progress updates
    start_time=$(date +%s)
    while true; do
        status=$(check_stack_status "$stack_name" "$region")
        current_time=$(date +%s)
        elapsed_time=$((current_time - start_time))
        
        # Format elapsed time
        elapsed_minutes=$((elapsed_time / 60))
        elapsed_seconds=$((elapsed_time % 60))
        
        case $status in
            CREATE_COMPLETE)
                print_status "Stack created successfully after ${elapsed_minutes}m ${elapsed_seconds}s!"
                break
                ;;
            CREATE_IN_PROGRESS)
                echo -ne "\r\033[K${GREEN}[INFO]${NC} Stack creation in progress... (${elapsed_minutes}m ${elapsed_seconds}s elapsed)"
                sleep 30
                ;;
            CREATE_FAILED|ROLLBACK_IN_PROGRESS|ROLLBACK_COMPLETE)
                print_error "Stack creation failed after ${elapsed_minutes}m ${elapsed_seconds}s with status: $status"
                print_error "Check the AWS CloudFormation console for error details"
                exit 1
                ;;
            *)
                print_error "Unexpected stack status: $status"
                exit 1
                ;;
        esac
    done
    
    # Save the stack ARN to a file for future reference
    echo "$stack_arn" > .stack_arn
    print_status "Stack ARN saved to .stack_arn"
else
    print_warning "Stack creation skipped."
fi

print_status "=========================================="
print_status "CloudFormation stack creation completed!"
print_status "Next step: Run create_hp_cluster.sh to configure the cluster"
print_status "=========================================="
