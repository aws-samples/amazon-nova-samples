#!/usr/bin/env bash

# HyperPod Cluster Configuration Script
# This script handles the HyperPod cluster setup and configuration

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
echo "HyperPod Cluster Configuration"
echo "=========================================="
echo

# Check prerequisites
if [ ! -f .stack_arn ]; then
    print_error "Stack ARN file (.stack_arn) not found. Please run create_cfn_stack.sh first."
    exit 1
fi

# Step 1: Install required tools
print_step "Step 1: Installing required tools"

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
        print_status "kubectl installed successfully"
    else
        print_error "kubectl is required. Exiting."
        exit 1
    fi
else
    print_status "kubectl is already installed: $(kubectl version --client)"
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
        print_status "eksctl installed successfully"
    else
        print_error "eksctl is required. Exiting."
        exit 1
    fi
else
    print_status "eksctl is already installed: $(eksctl version)"
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
        print_status "helm installed successfully"
    else
        print_error "helm is required. Exiting."
        exit 1
    fi
else
    print_status "helm is already installed: $(helm version --short)"
fi

# Step 2: Set environment variables
print_step "Step 2: Setting environment variables"

# Get stack name from .stack_arn file
stack_name=$(basename $(cat .stack_arn | cut -d'/' -f2))
region=$(cat .stack_arn | cut -d':' -f4)

export STACK_ID="$stack_name"
export AWS_REGION="$region"

print_status "Environment variables set:"
echo "STACK_ID=$STACK_ID"
echo "AWS_REGION=$AWS_REGION"

# Step 3: Configure environment
print_step "Step 3: Configuring environment"

if [ ! -f create_config.sh ]; then
    print_error "create_config.sh not found in current directory"
    exit 1
fi

print_status "Running create_config.sh..."
./create_config.sh

# Source environment variables
print_status "Sourcing environment variables..."
source env_vars

# Step 4: Update kubeconfig
print_step "Step 4: Updating kubeconfig"

if [ -n "$EKS_CLUSTER_NAME" ]; then
    print_status "Updating kubeconfig for cluster: $EKS_CLUSTER_NAME"
    aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME"
    print_status "kubeconfig updated successfully!"
else
    print_error "EKS_CLUSTER_NAME not set. Please check create_config.sh output."
    exit 1
fi

# Step 5: Configure SageMaker service model
print_step "Step 5: Configuring SageMaker service model"

if [ ! -f "sagemaker-2017-07-24.normal.json" ]; then
    print_error "SageMaker service model file not found: sagemaker-2017-07-24.normal.json"
    exit 1
fi

print_status "Adding SageMaker service model..."
aws configure add-model --service-model "file://$(pwd)/sagemaker-2017-07-24.normal.json" --service-name sagemaker

# Step 6: Get cluster configuration
print_step "Step 6: Getting cluster configuration"

print_status "Describing cluster configuration..."
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
    print_error "Failed to get cluster configuration. Please check if the cluster exists and you have proper permissions."
    exit 1
fi

print_status "Original cluster configuration saved to og_cluster_config.json"

# Step 7: Create new cluster configuration
print_step "Step 7: Creating new cluster configuration"

print_status "Creating new configuration file from original config..."

# Get values for RestrictedInstanceGroups
print_status "Please provide values for RestrictedInstanceGroups:"
restricted_instance_count=$(prompt_input "Enter instance count for restricted group" "2")
restricted_instance_type=$(prompt_input "Enter instance type for restricted group" "ml.p5.48xlarge")

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

print_status "Verifying execution role permissions..."
role_name=$(basename "$original_execution_role")
if ! aws iam get-role --role-name "$role_name" > /dev/null 2>&1; then
    print_error "Could not find execution role. Please ensure the role exists."
    exit 1
fi

# Update trust relationship
print_status "Updating trust relationship for role: $role_name"
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
print_status "Updating role permissions..."
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
print_status "Using execution role with updated permissions: $restricted_execution_role"
print_status "Storage configuration:"
echo
restricted_volume_size=$(prompt_input "Enter EBS volume size in GB" "500")
echo
print_status "FSx Lustre configuration:"
echo
restricted_fsx_size=$(prompt_input "Enter FSx Lustre size in GiB" "12000")
echo
restricted_fsx_throughput=$(prompt_input "Enter FSx Lustre per unit storage throughput" "125")
echo

# Create updated cluster configuration
print_status "Getting existing instance groups configuration..."
# Get VPC config from original configuration and ensure Subnets is set correctly
vpc_config=$(jq -c '.VpcConfig' og_cluster_config.json)
if [ -z "$vpc_config" ] || [ "$vpc_config" = "null" ]; then
    print_error "Could not find VPC configuration in original configuration"
    exit 1
fi

# Modify vpc_config to ensure Subnets is set to ['subnet-0e5b25a84860773a6']
vpc_config=$(echo $vpc_config)

existing_instance_groups=$(jq -c '.InstanceGroups | map({
    InstanceCount: .TargetCount,
    InstanceGroupName: .InstanceGroupName,
    InstanceType: .InstanceType,
    LifeCycleConfig: .LifeCycleConfig,
    ExecutionRole: .ExecutionRole,
    ThreadsPerCore: .ThreadsPerCore,
    InstanceStorageConfigs: .InstanceStorageConfigs,
    OnStartDeepHealthChecks: .OnStartDeepHealthChecks
} | del(.[] | nulls))' og_cluster_config.json)

cat > updated_cluster_config.json << EOF
{
  "ClusterName": "${HYPERPOD_CLUSTER_NAME}",
  "InstanceGroups": ${existing_instance_groups},
  "RestrictedInstanceGroups": [
    {
      "InstanceCount": ${restricted_instance_count},
      "InstanceGroupName": "restricted-instance-group",
      "InstanceType": "${restricted_instance_type}",
      "ExecutionRole": "${restricted_execution_role}",
      "ThreadsPerCore": 1,
      "InstanceStorageConfigs": [
        {
          "EbsVolumeConfig": {
            "VolumeSizeInGB": ${restricted_volume_size}
          }
        }
      ],
      "OverrideVpcConfig": ${vpc_config},
      "EnvironmentConfig": {
        "FSxLustreConfig": {
            "SizeInGiB": ${restricted_fsx_size},
            "PerUnitStorageThroughput": ${restricted_fsx_throughput}
        }
      }
    }
  ]
}
EOF

# Validate JSON
if ! jq '.' updated_cluster_config.json > /dev/null 2>&1; then
    print_error "Invalid JSON generated in updated_cluster_config.json"
    exit 1
fi

print_status "Created updated_cluster_config.json"
if prompt_yes_no "Do you want to review the new configuration?"; then
    cat updated_cluster_config.json
    if ! prompt_yes_no "Does the configuration look correct?"; then
        print_error "Please edit updated_cluster_config.json manually before continuing."
        exit 1
    fi
fi

# Step 8: Update cluster configuration
print_step "Step 8: Updating cluster configuration"

print_status "Updating cluster with new configuration..."
aws sagemaker update-cluster --cluster-name "$cluster_identifier" --cli-input-json file://updated_cluster_config.json

# Step 9: Verify cluster update
print_step "Step 9: Verifying cluster update"

print_status "Checking updated cluster configuration..."
aws sagemaker describe-cluster --region "$AWS_REGION" --cluster-name "$cluster_identifier"

echo
print_status "=========================================="
print_status "HyperPod cluster configuration completed!"
print_status "=========================================="

print_status "Next steps:"
echo "1. Verify your EKS cluster is running: kubectl get nodes"
echo "2. Check your HyperPod cluster status in the AWS console"
echo "3. Deploy your workloads to the cluster"

# Cleanup temporary files if any were created during execution
if [ -f "og_cluster_config.json" ] || [ -f "updated_cluster_config.json" ]; then
    if prompt_yes_no "Clean up temporary files (cluster config json files)?"; then
        rm -f og_cluster_config.json updated_cluster_config.json
        print_status "Temporary files cleaned up."
    fi
fi
