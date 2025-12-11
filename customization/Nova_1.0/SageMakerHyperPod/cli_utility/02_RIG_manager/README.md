# HyperPod RIG Manager

A utility for managing Restricted Instance Groups (RIGs) in HyperPod clusters. This tool provides functionality for adding, scaling, and deleting RIGs with comprehensive configuration options.

## Features

- **RIG Creation**: Add new Restricted Instance Groups
- **RIG Scaling**: Adjust instance counts for existing RIGs
- **RIG Deletion**: Remove existing RIGs
- **Configuration Management**: Handle VPC, storage, and execution settings
- **Interactive Interface**: Guided process for all operations

## Usage

```bash
./manage_rig.py [flags]
```

### Required Flags

- `cluster_arn`: ARN of the HyperPod cluster
- `--region`: AWS region

### Example Commands

```bash
# Add/Scale/Delete RIG
python3 manage_rig.py <cluster-arn> --region <aws-region>
```

## Operations

### 1. Add New RIG

Creates a new Restricted Instance Group with:

- Custom instance group name
- Instance count and type
- EBS volume configuration
- VPC settings (security groups, subnets)
- FSx Lustre configuration

### 2. Scale Existing RIG

Modify instance count for an existing RIG:

- Select RIG from available groups
- Specify new instance count
- Automatic configuration update

### 3. Delete RIG

Remove an existing RIG:

- Select RIG to delete
- Confirmation prompt
- Clean removal from cluster

## Configuration Options

### Instance Configuration

- **Instance Count**: Number of instances in the group
- **Instance Type**: AWS instance type (e.g., ml.p5.48xlarge)
- **Execution Role**: IAM role for instance execution

### Storage Configuration

1. **EBS Volume**

   - Volume size in GB
   - Default: 500GB

2. **FSx Lustre**
   - Size in GiB
   - Per unit storage throughput
   - Default: 12000 GiB, 125 MB/s/TiB

### VPC Configuration

- Security group IDs
- Subnet IDs
- Network configuration

## Best Practices

1. **RIG Creation**

   - Use descriptive instance group names
   - Configure appropriate storage sizes
   - Set proper security group permissions

2. **Scaling**

   - Monitor resource utilization before scaling
   - Ensure subnet capacity for new instances
   - Verify storage requirements

3. **Deletion**
   - Verify no active workloads
   - Check dependencies before removal
   - Maintain at least one active RIG

## Error Handling

The utility handles various error scenarios:

- Invalid cluster configuration
- Missing RIG setup
- AWS API errors
- Configuration validation failures

## Requirements

- Python 3.x
- AWS CLI configured with appropriate permissions
- Valid HyperPod cluster with initial RIG setup
- Appropriate IAM roles and permissions

## Configuration File

The tool generates an updated configuration file (`updated_cluster_config.json`) containing:

- Complete cluster configuration
- RIG specifications
- Storage settings
- Network configuration

## Important Notes

- Initial RIG setup must be completed using `00_setup/create_hp_cluster.sh`
- Configuration changes are validated before application
- Updates are applied asynchronously
- Monitor AWS Console for update status
