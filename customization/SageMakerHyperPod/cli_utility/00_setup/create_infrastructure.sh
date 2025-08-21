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

# 🚀 HyperPod EKS Infrastructure Setup Script
# 
# This script creates the foundational AWS infrastructure for HyperPod clusters:
# - Sets up EKS cluster for Kubernetes orchestration
# - Creates VPC, subnets, and networking components
# - Configures IAM roles and security groups
# - Provisions initial compute instances for ML workloads
#
# Prerequisites:
# - AWS CLI configured with appropriate permissions
# - Sudo access for installing required tools
# - Internet connection for downloading dependencies
#
# What this script does:
# 1. Installs required tools (jq, AWS CLI)
# 2. Collects configuration parameters interactively
# 3. Downloads CloudFormation template from AWS samples
# 4. Creates and monitors CloudFormation stack deployment
# 5. Saves stack information for subsequent setup steps

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
echo "🚀 HyperPod EKS Infrastructure Setup"
echo "=========================================="
echo
echo "This script will create the foundational AWS infrastructure for your HyperPod cluster."
echo "The process typically takes 20-30 minutes and includes:"
echo "  • EKS cluster creation"
echo "  • VPC and networking setup"
echo "  • IAM roles and security configuration"
echo "  • Initial compute instance provisioning"
echo
print_warning "Sudo access required for installing system dependencies (jq, AWS CLI)"
# Check if we have sudo access
if ! sudo -v >/dev/null 2>&1; then
    print_error "This script requires sudo access for installing packages. Please run with sudo privileges."
    exit 1
fi

# Step 0: Prerequisites Installation
print_step "Step 0: Installing Required Dependencies"
echo "Installing tools needed for CloudFormation deployment and JSON processing..."
echo

# 0.0 Install jq (JSON processor)
print_status "Checking jq installation (needed for JSON parameter processing)..."
if ! command_exists jq; then
    print_warning "jq not found. This tool is required for processing CloudFormation parameters."
    if prompt_yes_no "Install jq JSON processor?"; then
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
print_status "Checking AWS CLI installation (required for CloudFormation operations)..."
if ! command_exists aws; then
    print_warning "AWS CLI not found. This is required for creating AWS infrastructure."
    if prompt_yes_no "Install AWS CLI version 2?"; then
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
print_step "Step 1: Infrastructure Configuration"
echo "Configure your HyperPod cluster settings. Press Enter to use defaults or provide custom values."
echo "Tip: For production workloads, consider using larger instance types and counts."
echo

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
    "🏧 Create new EKS cluster stack (recommended: true for new setups)"
    "📝 EKS cluster name (will be used for kubectl configuration)"
    "🔄 Node recovery strategy (None/Automatic - how to handle failed nodes)"
    "🏷️ HyperPod cluster name (unique identifier for your ML cluster)"
    "💼 Resource name prefix (helps organize AWS resources)"
    "🌍 Availability Zone ID (e.g., use1-az2 for us-east-1b)"
    "⚡ GPU instance type (ml.g5.8xlarge=8 A10G GPUs, ml.p5.48xlarge=8 H100 GPUs)"
    "📊 Number of GPU instances to launch initially"
    "🛠️ Create general purpose instances (false saves costs, true adds CPU nodes)"
)

print_status "Configure your HyperPod infrastructure parameters:"
echo "Each parameter has a recommended default value. Customize as needed for your use case."
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

# Step 3: Infrastructure Deployment
print_step "Step 3: Deploying AWS Infrastructure"
echo "Downloading the official AWS CloudFormation template for HyperPod EKS integration..."
echo "This template creates a complete ML infrastructure stack including:"
echo "  • EKS cluster with managed node groups"
echo "  • VPC with public/private subnets"
echo "  • Security groups and IAM roles"
echo "  • HyperPod cluster configuration"
echo

print_status "Downloading CloudFormation template from AWS samples repository..."
curl -O https://raw.githubusercontent.com/aws-samples/awsome-distributed-training/refs/heads/main/1.architectures/7.sagemaker-hyperpod-eks/cfn-templates/nested-stacks/main-stack.yaml

echo
print_status "Final deployment configuration:"
stack_name=$(prompt_input "Enter CloudFormation stack name (must be unique in your account)" "hp-eks-test-stack")
region=$(prompt_input "Enter AWS region (where your infrastructure will be created)" "us-east-1")
echo
print_status "Stack will be created in region: $region"
print_status "Stack name: $stack_name"

echo
print_warning "IMPORTANT: Stack creation will incur AWS charges for the resources created."
print_status "Ready to create CloudFormation stack: $stack_name"
print_status "Estimated deployment time: 20-30 minutes"
print_status "Resources that will be created: EKS cluster, EC2 instances, VPC, IAM roles"
echo
if prompt_yes_no "Proceed with infrastructure deployment?"; then
    # Create the stack and capture the stack ARN
    stack_arn=$(aws cloudformation create-stack \
        --stack-name "$stack_name" \
        --template-body file://main-stack.yaml \
        --region "$region" \
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
        --parameters file://params.json \
        --query 'StackId' \
        --output text)
    
    print_status "Stack deployment initiated successfully!"
    print_status "Stack ARN: $stack_arn"
    echo
    print_status "Monitoring deployment progress (this typically takes 20-30 minutes)..."
    print_status "You can also monitor progress in the AWS CloudFormation console"
    echo
    
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
    print_status "Stack ARN saved to .stack_arn file for next setup step"
else
    print_warning "Stack creation skipped."
fi

# Function to display infrastructure status
display_infrastructure_status() {
    local stack_name="$1"
    local region="$2"
    
    echo
    print_step "Infrastructure Status Report"
    echo "Retrieving current infrastructure information from AWS..."
    echo
    
    # Check if stack exists
    if ! aws cloudformation describe-stacks --stack-name "$stack_name" --region "$region" >/dev/null 2>&1; then
        print_warning "Stack '$stack_name' not found or not accessible"
        return 1
    fi
    
    # Get stack outputs
    print_status "📋 CloudFormation Stack Information:"
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$region" \
        --query 'Stacks[0].{StackName:StackName,Status:StackStatus,CreationTime:CreationTime}' \
        --output table
    
    # Get EKS cluster info
    eks_cluster_name=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$region" \
        --query 'Stacks[0].Outputs[?OutputKey==`EKSClusterName`].OutputValue' \
        --output text 2>/dev/null || echo "N/A")
    
    if [ "$eks_cluster_name" != "N/A" ] && [ -n "$eks_cluster_name" ]; then
        echo
        print_status "🏗️ EKS Cluster Information:"
        aws eks describe-cluster \
            --name "$eks_cluster_name" \
            --region "$region" \
            --query 'cluster.{Name:name,Status:status,Version:version,Endpoint:endpoint,CreatedAt:createdAt}' \
            --output table 2>/dev/null || print_warning "EKS cluster details not accessible"
        
        echo
        print_status "👥 EKS Node Groups:"
        aws eks list-nodegroups \
            --cluster-name "$eks_cluster_name" \
            --region "$region" \
            --query 'nodegroups' \
            --output table 2>/dev/null || print_warning "Node groups not accessible"
    fi
    
    # Get VPC info
    vpc_id=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$region" \
        --query 'Stacks[0].Outputs[?OutputKey==`VpcId`].OutputValue' \
        --output text 2>/dev/null || echo "N/A")
    
    if [ "$vpc_id" != "N/A" ] && [ -n "$vpc_id" ]; then
        echo
        print_status "🌐 VPC Information:"
        aws ec2 describe-vpcs \
            --vpc-ids "$vpc_id" \
            --region "$region" \
            --query 'Vpcs[0].{VpcId:VpcId,CidrBlock:CidrBlock,State:State}' \
            --output table 2>/dev/null || print_warning "VPC details not accessible"
        
        echo
        print_status "🔗 Subnets:"
        aws ec2 describe-subnets \
            --filters "Name=vpc-id,Values=$vpc_id" \
            --region "$region" \
            --query 'Subnets[].{SubnetId:SubnetId,CidrBlock:CidrBlock,AvailabilityZone:AvailabilityZone,Type:Tags[?Key==`Name`].Value|[0]}' \
            --output table 2>/dev/null || print_warning "Subnet details not accessible"
    fi
    
    # Get EC2 instances
    echo
    print_status "💻 EC2 Instances (HyperPod nodes):"
    aws ec2 describe-instances \
        --region "$region" \
        --filters "Name=tag:aws:cloudformation:stack-name,Values=$stack_name" "Name=instance-state-name,Values=running,pending,stopping,stopped" \
        --query 'Reservations[].Instances[].{InstanceId:InstanceId,InstanceType:InstanceType,State:State.Name,LaunchTime:LaunchTime,PrivateIpAddress:PrivateIpAddress}' \
        --output table 2>/dev/null || print_warning "EC2 instances not accessible"
    
    # Get SageMaker HyperPod cluster info
    hyperpod_cluster_name=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$region" \
        --query 'Stacks[0].Outputs[?OutputKey==`HyperPodClusterName`].OutputValue' \
        --output text 2>/dev/null || echo "N/A")
    
    if [ "$hyperpod_cluster_name" != "N/A" ] && [ -n "$hyperpod_cluster_name" ]; then
        echo
        print_status "🚀 SageMaker HyperPod Cluster:"
        aws sagemaker describe-cluster \
            --cluster-name "$hyperpod_cluster_name" \
            --region "$region" \
            --query '{ClusterName:ClusterName,ClusterStatus:ClusterStatus,CreationTime:CreationTime,InstanceGroups:InstanceGroups[].{GroupName:InstanceGroupName,InstanceType:InstanceType,InstanceCount:CurrentCount}}' \
            --output table 2>/dev/null || print_warning "HyperPod cluster details not accessible"
    fi
    
    # Get IAM roles created by the stack
    echo
    print_status "🔐 IAM Roles:"
    aws cloudformation list-stack-resources \
        --stack-name "$stack_name" \
        --region "$region" \
        --query 'StackResourceSummaries[?ResourceType==`AWS::IAM::Role`].{LogicalId:LogicalResourceId,PhysicalId:PhysicalResourceId,Status:ResourceStatus}' \
        --output table 2>/dev/null || print_warning "IAM roles not accessible"
    
    # Get security groups
    echo
    print_status "🛡️ Security Groups:"
    aws cloudformation list-stack-resources \
        --stack-name "$stack_name" \
        --region "$region" \
        --query 'StackResourceSummaries[?ResourceType==`AWS::EC2::SecurityGroup`].{LogicalId:LogicalResourceId,PhysicalId:PhysicalResourceId,Status:ResourceStatus}' \
        --output table 2>/dev/null || print_warning "Security groups not accessible"
    
    # Summary of installed tools
    echo
    print_status "🛠️ Installed Tools Summary:"
    printf "%-20s %-30s %-10s\n" "Tool" "Version" "Status"
    printf "%-20s %-30s %-10s\n" "----" "-------" "------"
    
    # Check jq
    if command_exists jq; then
        jq_version=$(jq --version 2>/dev/null || echo "Unknown")
        printf "%-20s %-30s %-10s\n" "jq" "$jq_version" "✅ Installed"
    else
        printf "%-20s %-30s %-10s\n" "jq" "N/A" "❌ Missing"
    fi
    
    # Check AWS CLI
    if command_exists aws; then
        aws_version=$(aws --version 2>/dev/null | cut -d' ' -f1 || echo "Unknown")
        printf "%-20s %-30s %-10s\n" "AWS CLI" "$aws_version" "✅ Installed"
    else
        printf "%-20s %-30s %-10s\n" "AWS CLI" "N/A" "❌ Missing"
    fi
    
    # Check kubectl (if available)
    if command_exists kubectl; then
        kubectl_version=$(kubectl version --client --short 2>/dev/null | cut -d' ' -f3 || echo "Unknown")
        printf "%-20s %-30s %-10s\n" "kubectl" "$kubectl_version" "✅ Installed"
    else
        printf "%-20s %-30s %-10s\n" "kubectl" "N/A" "⚠️ Not installed"
    fi
    
    echo
    print_status "📊 Resource Cost Estimation:"
    echo "Note: Use AWS Pricing Calculator for detailed cost estimates"
    echo "https://calculator.aws"
}

echo
print_status "==========================================="
print_status "✅ Infrastructure deployment completed successfully!"
print_status "==========================================="
echo
print_status "What was created:"
echo "  • EKS cluster for Kubernetes orchestration"
echo "  • VPC with secure networking configuration"
echo "  • IAM roles with appropriate permissions"
echo "  • Initial compute instances for ML workloads"
echo

# Display comprehensive infrastructure status
if [ -n "$stack_name" ] && [ -n "$region" ]; then
    display_infrastructure_status "$stack_name" "$region"
fi

echo
print_status "Next Steps:"
echo "  1. Run './create_hp_cluster.sh' to configure the HyperPod cluster"
echo "  2. This will install kubectl, eksctl, and helm"
echo "  3. Configure cluster access and restricted instance groups"
echo
print_status "Files created:"
echo "  • .stack_arn - Contains your CloudFormation stack ARN"
echo "  • params.json - Your infrastructure configuration"
echo "  • main-stack.yaml - CloudFormation template"
echo
print_status "Cleanup:"
echo "  • Run './cleanup_infrastructure.sh' to delete all infrastructure when done"
echo
print_warning "Keep the .stack_arn file - it's needed for the next setup step!"
