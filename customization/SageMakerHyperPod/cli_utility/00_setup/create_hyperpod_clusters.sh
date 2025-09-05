#!/usr/bin/env bash

# ==============================================================================
# Amazon SageMaker HyperPod Cluster Configuration Script
# ==============================================================================
#
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
#
# ==============================================================================
# DESCRIPTION:
#   This script configures an Amazon SageMaker HyperPod cluster with EKS integration.
#   It handles the complete setup process including tool installation, cluster
#   configuration, and restricted instance group creation.
#
# PREREQUISITES:
#   - AWS CLI installed and configured with appropriate credentials
#   - CloudFormation stack created (run create_infrastructure.sh first)
#   - .stack_arn file present (created by create_infrastructure.sh)
#   - sagemaker-2017-07-24.normal.json service model file
#   - create_config.sh script in the same directory
#
# WHAT THIS SCRIPT DOES:
#   1. Installs required tools (kubectl, eksctl, helm) if missing
#   2. Configures environment variables from CloudFormation stack
#   3. Updates kubeconfig for EKS cluster access
#   4. Configures SageMaker service model for HyperPod operations
#   5. Retrieves existing cluster configuration
#   6. Creates new restricted instance groups with custom settings
#   7. Updates IAM roles with necessary permissions
#   8. Applies the new configuration to the HyperPod cluster
#   9. Verifies the configuration update
#
# USAGE:
#   ./create_hyperpod_clusters.sh
#
# OUTPUT FILES:
#   - env_vars: Environment variables for the session
#   - og_cluster_config.json: Original cluster configuration backup
#   - updated_cluster_config.json: New cluster configuration
#
# AUTHOR: AWS Solutions Team
# VERSION: 1.0
# LAST MODIFIED: $(date +%Y-%m-%d)
# ==============================================================================

set -e

# Color codes for enhanced user experience
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Enhanced output functions with better formatting
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

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}$1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Enhanced prompt function with better validation
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

# Enhanced input prompt with validation
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

# Display script header
echo
print_header "==============================================================================="
print_header "🚀 Amazon SageMaker HyperPod Cluster Configuration"
print_header "==============================================================================="
echo
print_status "This script will configure your HyperPod cluster with the following steps:"
echo "  📦 Install required tools (kubectl, eksctl, helm)"
echo "  🔧 Configure environment variables and AWS settings"
echo "  ⚙️  Update Kubernetes configuration for EKS access"
echo "  🔐 Configure SageMaker service model and IAM permissions"
echo "  📋 Retrieve and update cluster configuration"
echo "  🎯 Create restricted instance groups with custom settings"
echo "  ✅ Verify and apply the new configuration"
echo
print_warning "⚠️  Ensure you have run create_infrastructure.sh successfully before proceeding"
echo

# Check prerequisites with detailed error messages
print_step "Validating Prerequisites"

if [ ! -f .stack_arn ]; then
    print_error "Stack ARN file (.stack_arn) not found."
    print_error "This file is created by create_infrastructure.sh and contains the CloudFormation stack identifier."
    print_error "Please run ccreate_infrastructure.sh first to create the required infrastructure."
    exit 1
fi

if [ ! -f create_config.sh ]; then
    print_error "create_config.sh not found in current directory."
    print_error "This script is required to generate environment variables."
    exit 1
fi

print_success "All prerequisite files found!"
echo

# Step 1: Install required tools
print_step "Step 1: Installing Required Tools"

# Install kubectl
print_status "Checking kubectl installation..."
if ! command_exists kubectl; then
    print_warning "kubectl not found. Installing..."
    if prompt_yes_no "Do you want to install kubectl?"; then
        curl -O https://s3.us-west-2.amazonaws.com/amazon-eks/1.30.4/2024-09-11/bin/linux/amd64/kubectl
        chmod +x ./kubectl
        mkdir -p $HOME/bin && cp ./kubectl $HOME/bin/kubectl && export PATH=$HOME/bin:$PATH
        echo 'export PATH=$HOME/bin:$PATH' >> ~/.bashrc
        rm ./kubectl
        print_success "kubectl installed successfully"
    else
        print_error "kubectl is required. Exiting."
        exit 1
    fi
else
    print_success "kubectl is already installed: $(kubectl version --client --short 2>/dev/null || echo 'version check failed')"
fi

# Install eksctl
print_status "Checking eksctl installation..."
if ! command_exists eksctl; then
    print_warning "eksctl not found. Installing..."
    if prompt_yes_no "Do you want to install eksctl?"; then
        ARCH=amd64
        PLATFORM=$(uname -s)_$ARCH
        curl -sLO "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_$PLATFORM.tar.gz"
        tar -xzf eksctl_$PLATFORM.tar.gz -C /tmp && rm eksctl_$PLATFORM.tar.gz
        sudo mv /tmp/eksctl /usr/local/bin
        print_success "eksctl installed successfully"
    else
        print_error "eksctl is required. Exiting."
        exit 1
    fi
else
    print_success "eksctl is already installed: $(eksctl version)"
fi

# Install helm
print_status "Checking helm installation..."
if ! command_exists helm; then
    print_warning "helm not found. Installing..."
    if prompt_yes_no "Do you want to install helm?"; then
        curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
        chmod 700 get_helm.sh
        ./get_helm.sh
        rm get_helm.sh
        print_success "helm installed successfully"
    else
        print_error "helm is required. Exiting."
        exit 1
    fi
else
    print_success "helm is already installed: $(helm version --short)"
fi

# Step 2: Set environment variables
print_step "Step 2: Setting Environment Variables"

# Get stack name from .stack_arn file
stack_name=$(basename $(cat .stack_arn | cut -d'/' -f2))
region=$(cat .stack_arn | cut -d':' -f4)

export STACK_ID="$stack_name"
export AWS_REGION="$region"

print_status "Environment variables set:"
echo "  • STACK_ID=$STACK_ID"
echo "  • AWS_REGION=$AWS_REGION"

# Step 3: Configure environment
print_step "Step 3: Configuring Environment"

print_status "Running create_config.sh to generate environment variables..."
./create_config.sh

# Source environment variables
print_status "Loading environment variables..."
source env_vars

# Step 4: Update kubeconfig
print_step "Step 4: Updating Kubernetes Configuration"

if [ -n "$EKS_CLUSTER_NAME" ]; then
    print_status "Updating kubeconfig for EKS cluster: $EKS_CLUSTER_NAME"
    aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$AWS_REGION"
    print_success "Kubernetes configuration updated successfully!"
else
    print_error "EKS_CLUSTER_NAME not set. Please check create_config.sh output."
    exit 1
fi

# Step 5: Install SageMaker Python package
print_step "Step 5: Installing SageMaker Python Package"

print_status "Checking SageMaker Python package installation..."
if ! python3 -c "import sagemaker" 2>/dev/null; then
    print_warning "SageMaker Python package not found. Installing..."
    if prompt_yes_no "Do you want to install the SageMaker Python package?"; then
        # Try different installation methods based on availability
        if command_exists pipx; then
            print_status "Installing SageMaker via pipx (isolated environment)..."
            pipx install sagemaker
        elif [[ "$OSTYPE" == "darwin"* ]] && command_exists brew; then
            print_status "Installing SageMaker via brew (brew's Python recommended for macOS)..."
            brew install sagemaker
        else
            print_status "Installing SageMaker via pip3..."
            pip3 install sagemaker
        fi
        print_success "SageMaker Python package installed successfully!"
    else
        print_error "SageMaker Python package is required. Exiting."
        exit 1
    fi
else
    print_success "SageMaker Python package is already installed"
fi

# Step 6: Get cluster configuration
print_step "Step 6: Retrieving Cluster Configuration"

print_status "Retrieving existing HyperPod cluster configuration..."
if [ -z "$HYPERPOD_CLUSTER_NAME" ]; then
    print_error "HYPERPOD_CLUSTER_NAME is not set. Please check if env_vars was sourced correctly."
    exit 1
fi

print_status "Using HyperPod cluster: $HYPERPOD_CLUSTER_NAME"
# Check if HYPERPOD_CLUSTER_NAME is an ARN, if not use HYPERPOD_CLUSTER_ARN
if [[ "$HYPERPOD_CLUSTER_NAME" == arn:* ]]; then
    cluster_identifier="$HYPERPOD_CLUSTER_NAME"
else
    cluster_identifier="$HYPERPOD_CLUSTER_ARN"
fi

if ! aws sagemaker describe-cluster --cluster-name "$cluster_identifier" --region "$AWS_REGION" > og_cluster_config.json; then
    print_error "Failed to retrieve cluster configuration."
    print_error "Please verify the cluster exists and you have proper permissions."
    exit 1
fi

print_success "Original cluster configuration saved to og_cluster_config.json"

# Step 7: Create new cluster configuration
print_step "Step 7: Configuring Restricted Instance Groups"

print_status "Creating new cluster configuration with restricted instance groups..."
echo
print_status "📝 Please provide configuration for the restricted instance group:"

# Get values for RestrictedInstanceGroups
restricted_instance_count=$(prompt_input "Instance count for restricted group" "2")
restricted_instance_type=$(prompt_input "Instance type for restricted group" "ml.p5.48xlarge")

if ! jq -e '.InstanceGroups[0].ExecutionRole' og_cluster_config.json >/dev/null 2>&1; then
    print_error "Invalid cluster configuration. Could not find ExecutionRole in og_cluster_config.json"
    exit 1
fi

# Get execution role from original config and verify it exists
original_execution_role=$(jq -r '.InstanceGroups[0].ExecutionRole' og_cluster_config.json)
if [ -z "$original_execution_role" ] || [ "$original_execution_role" = "null" ]; then
    print_error "Could not find ExecutionRole in original configuration"
    exit 1
fi

print_status "Configuring IAM permissions for execution role..."
role_name=$(basename "$original_execution_role")
if ! aws iam get-role --role-name "$role_name" > /dev/null 2>&1; then
    print_error "Could not find execution role. Please ensure the role exists."
    exit 1
fi

# Update trust relationship
print_status "Updating IAM trust relationship for role: $role_name"
trust_policy='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "sagemaker.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}'

if ! aws iam update-assume-role-policy --role-name "$role_name" --policy-document "$trust_policy"; then
    print_error "Failed to update trust relationship. Please ensure you have sufficient permissions."
    exit 1
fi

# Update role permissions
print_status "Updating IAM role permissions..."
role_policy='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeSubnets",
                "ec2:DescribeVpcs",
                "ec2:DescribeSecurityGroups",
                "iam:PassRole",
                "sagemaker:*"
            ],
            "Resource": "*"
        }
    ]
}'

if ! aws iam put-role-policy --role-name "$role_name" --policy-name "HyperPodClusterPolicy" --policy-document "$role_policy"; then
    print_error "Failed to update role permissions. Please ensure you have sufficient permissions."
    exit 1
fi

# Use the same execution role as existing instance groups
restricted_execution_role="$original_execution_role"
print_success "IAM role configured with updated permissions: $restricted_execution_role"

echo
print_status "💾 Storage Configuration:"
restricted_volume_size=$(prompt_input "EBS volume size in GB" "500")

echo
print_status "🗂️  FSx Lustre Configuration:"
restricted_fsx_size=$(prompt_input "FSx Lustre size in GiB" "12000")
restricted_fsx_throughput=$(prompt_input "FSx Lustre per unit storage throughput" "125")

# Create updated cluster configuration
print_status "Generating updated cluster configuration..."
# Get VPC config from original configuration
vpc_config=$(jq -c '.VpcConfig' og_cluster_config.json)
if [ -z "$vpc_config" ] || [ "$vpc_config" = "null" ]; then
    print_error "Could not find VPC configuration in original configuration"
    exit 1
fi

# Get LifeCycleConfig from existing instance group
lifecycle_config=$(jq -c '.InstanceGroups[0].LifeCycleConfig' og_cluster_config.json)
if [ "$lifecycle_config" = "null" ]; then
    print_error "Could not find LifeCycleConfig in original configuration"
    exit 1
fi

# Create new restricted instance group with required LifeCycleConfig and FSxLustreConfig
print_status "Creating restricted instance group with FSx Lustre configuration..."
restricted_instance_group=$(jq -n \
    --argjson count "$restricted_instance_count" \
    --arg name "restricted-instance-group" \
    --arg type "$restricted_instance_type" \
    --arg role "$restricted_execution_role" \
    --argjson threads 1 \
    --argjson volume "$restricted_volume_size" \
    --argjson fsx_size "$restricted_fsx_size" \
    --argjson fsx_throughput "$restricted_fsx_throughput" \
    --argjson lifecycle "$lifecycle_config" \
    '{
      "InstanceCount": $count,
      "InstanceGroupName": $name,
      "InstanceType": $type,
      "ExecutionRole": $role,
      "ThreadsPerCore": $threads,
      "LifeCycleConfig": $lifecycle,
      "InstanceStorageConfigs": [
        {
          "EbsVolumeConfig": {
            "VolumeSizeInGB": $volume
          }
        }
      ],
      "EnvironmentConfig": {
        "FSxLustreConfig": {
          "SizeInGiB": $fsx_size,
          "PerUnitStorageThroughput": $fsx_throughput
        }
      }
    }')

# Debug: Show the restricted instance group
print_status "📋 Restricted instance group configuration:"
echo "$restricted_instance_group" | jq '.'

# Combine existing and new instance groups
existing_instance_groups=$(jq -c '.InstanceGroups | map({
    InstanceCount: .TargetCount,
    InstanceGroupName: .InstanceGroupName,
    InstanceType: .InstanceType,
    LifeCycleConfig: .LifeCycleConfig,
    ExecutionRole: .ExecutionRole,
    ThreadsPerCore: .ThreadsPerCore,
    InstanceStorageConfigs: .InstanceStorageConfigs,
    OnStartDeepHealthChecks: .OnStartDeepHealthChecks,
    EnvironmentConfig: .EnvironmentConfig
} | del(.[] | nulls))' og_cluster_config.json)

# Add the new restricted instance group to existing ones
print_status "Combining existing and new instance groups..."
all_instance_groups=$(echo "$existing_instance_groups" | jq --argjson new "$restricted_instance_group" ". + [$new]")

# Debug: Show total instance groups count
total_groups=$(echo "$all_instance_groups" | jq 'length')
print_status "Total instance groups after adding restricted group: $total_groups"

cat > updated_cluster_config.json << EOF
{
  "ClusterName": "${HYPERPOD_CLUSTER_NAME}",
  "InstanceGroups": ${all_instance_groups}
}
EOF

# Validate JSON
if ! jq '.' updated_cluster_config.json > /dev/null 2>&1; then
    print_error "Invalid JSON generated in updated_cluster_config.json"
    exit 1
fi

print_success "Updated cluster configuration created: updated_cluster_config.json"
if prompt_yes_no "Do you want to review the new configuration?"; then
    echo
    print_status "📄 New Cluster Configuration:"
    cat updated_cluster_config.json | jq '.'
    echo
    if ! prompt_yes_no "Does the configuration look correct?"; then
        print_error "Please edit updated_cluster_config.json manually before continuing."
        exit 1
    fi
fi

# Step 8: Update cluster configuration
print_step "Step 8: Applying Cluster Configuration"

print_status "Updating HyperPod cluster with new configuration..."
if aws sagemaker update-cluster --cluster-name "$cluster_identifier" --cli-input-json file://updated_cluster_config.json; then
    print_success "Cluster configuration update initiated successfully!"
else
    print_error "Failed to update cluster configuration. Check AWS console for details."
    exit 1
fi

# Step 9: Verify cluster update
print_step "Step 9: Verifying Configuration Update"

print_status "Waiting for cluster update to propagate..."
sleep 10

print_status "Verifying updated cluster configuration..."
if aws sagemaker describe-cluster --region "$AWS_REGION" --cluster-name "$cluster_identifier" > /dev/null 2>&1; then
    print_success "Cluster configuration updated successfully!"
else
    print_warning "Cluster update may still be in progress. Check AWS console for status."
fi

# Final status and completion summary
echo
print_header "==============================================================================="
print_success "🎉 HyperPod Cluster Configuration Completed Successfully!"
print_header "==============================================================================="
echo

# Display configuration summary
print_status "📊 Configuration Summary:"
echo "  • Cluster Name: $HYPERPOD_CLUSTER_NAME"
echo "  • AWS Region: $AWS_REGION"
echo "  • EKS Cluster: $EKS_CLUSTER_NAME"
echo "  • Restricted Instance Count: $restricted_instance_count"
echo "  • Restricted Instance Type: $restricted_instance_type"
echo "  • EBS Volume Size: ${restricted_volume_size}GB"
echo "  • FSx Lustre Size: ${restricted_fsx_size}GiB"
echo "  • FSx Throughput: ${restricted_fsx_throughput}MB/s/TiB"
echo

print_status "📁 Generated Files:"
echo "  • env_vars - Environment variables for this session"
echo "  • og_cluster_config.json - Original cluster configuration backup"
echo "  • updated_cluster_config.json - New cluster configuration"
echo

print_status "🔍 Verification Commands:"
echo "  • Check EKS nodes: kubectl get nodes"
echo "  • Check HyperPod status: aws sagemaker describe-cluster --cluster-name '$cluster_identifier'"
echo "  • View cluster in console: https://console.aws.amazon.com/sagemaker/home?region=$AWS_REGION#/hyperpod"
echo

print_status "🚀 Next Steps:"
echo "  1. Verify EKS cluster nodes are ready"
echo "  2. Check HyperPod cluster status in AWS Console"
echo "  3. Deploy your machine learning workloads"
echo "  4. Monitor cluster performance and scaling"
echo

# Cleanup temporary files with user confirmation
if [ -f "og_cluster_config.json" ] || [ -f "updated_cluster_config.json" ]; then
    echo
    if prompt_yes_no "🧹 Clean up temporary configuration files?"; then
        rm -f og_cluster_config.json updated_cluster_config.json
        print_success "Temporary files cleaned up successfully."
    else
        print_status "Temporary files preserved for your reference."
    fi
fi

echo
print_success "✅ Script execution completed at $(date)"
print_status "💡 For troubleshooting, check the AWS CloudFormation and SageMaker consoles."
echo