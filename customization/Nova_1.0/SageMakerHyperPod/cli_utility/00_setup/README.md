# HyperPod EKS Cluster Configuration

This repository contains scripts to set up and configure a HyperPod cluster with EKS integration.

## Prerequisites

- AWS CLI installed and configured with appropriate credentials
- jq installed (will be installed by script if missing)
- kubectl installed (will be installed by script if missing)
- eksctl installed (will be installed by script if missing)
- helm installed (will be installed by script if missing)

## Step-by-Step Execution

### 1. Create CloudFormation Stack

First, run the CloudFormation stack creation script:

```bash
./create_cfn_stack.sh
```

This script will:

- Install required tools if missing (jq, AWS CLI)
- Prompt for configuration parameters
- Create CloudFormation stack with EKS cluster
- Save stack ARN to .stack_arn file
- Wait for stack creation to complete (20-30 minutes)

### 2. Configure HyperPod Cluster

After the CloudFormation stack is created successfully, run:

```bash
./create_hp_cluster.sh
```

This script will:

- Install required tools if missing (kubectl, eksctl, helm)
- Configure environment using create_config.sh
- Update kubeconfig for EKS cluster access
- Configure SageMaker service model
- Update cluster configuration with:
  - Existing instance groups
  - New restricted instance groups
  - VPC configuration
  - Storage settings

You will be prompted to provide: (you can keep the default)

- Instance count for restricted group
- Instance type for restricted group
- EBS volume size
- FSx Lustre configuration

### 3. Verify Configuration

After both scripts complete successfully:

1. Check EKS cluster nodes:

```bash
kubectl get nodes
```

2. Verify HyperPod cluster status in AWS Console:

   - Go to SageMaker > HyperPod
   - Check cluster status and configuration

3. Deploy your workloads to the cluster

## Files

- `create_cfn_stack.sh`: Creates CloudFormation stack with EKS cluster
- `create_hp_cluster.sh`: Configures HyperPod cluster and instance groups
- `create_config.sh`: Sets up environment variables (created by scripts)
- `.stack_arn`: Contains CloudFormation stack ARN (created by scripts)
- `env_vars`: Contains environment variables (created by scripts)

## Important Notes

- Ensure you have appropriate AWS permissions for:
  - CloudFormation stack creation
  - EKS cluster management
  - IAM role/policy modifications
  - SageMaker HyperPod operations
- Scripts will preserve existing instance groups and VPC configuration
- All configuration files are generated in the current directory

