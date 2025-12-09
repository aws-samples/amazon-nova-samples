# Bedrock Model Export and Provisioned Throughput Setup

This tool facilitates the process of exporting trained models to Amazon Bedrock and setting up provisioned throughput for inference. It provides a streamlined workflow for:

- Importing custom models from S3 to Bedrock
- Monitoring model creation status
- Setting up provisioned throughput (optional)
- Monitoring provisioned throughput setup

## Prerequisites

1. Python 3.x
2. AWS credentials configured with appropriate permissions
3. Required Python packages:
   ```bash
   pip install boto3
   ```
4. IAM role with necessary permissions for:
   - Bedrock model creation
   - S3 access
   - Provisioned throughput setup

## Installation

1. Clone the repository or copy the `model_copy_to_br.py` script to your local machine
2. Ensure you have the prerequisites installed
3. Make the script executable (Unix-based systems):
   ```bash
   chmod +x model_copy_to_br.py
   ```

## Usage

### Basic Syntax

```bash
python model_copy_to_br.py -m <model-name> -s <s3-uri> -a <role-arn> [-p <provisioned-units>] [-r <region>] [-i <interval>]
```

### Parameters

| Parameter         | Flag                      | Description                            | Required | Default   |
| ----------------- | ------------------------- | -------------------------------------- | -------- | --------- |
| Model Name        | `-m, --model-name`        | Name for the Bedrock model             | Yes      | -         |
| S3 URI            | `-s, --s3-uri`            | S3 URI where model is stored           | Yes      | -         |
| Role ARN          | `-a, --role-arn`          | IAM role ARN for model creation        | Yes      | -         |
| Provisioned Units | `-p, --provisioned-units` | Number of provisioned throughput units | No       | None      |
| Region            | `-r, --region`            | AWS region                             | No       | us-east-1 |
| Check Interval    | `-i, --interval`          | Status check interval in seconds       | No       | 10        |

### Examples

1. Create model without provisioned throughput:

   ```bash
   python model_copy_to_br.py \
     -m my-custom-model \
     -s s3://my-bucket/model-path/ \
     -a arn:aws:iam::123456789012:role/MyRole
   ```

2. Create model with provisioned throughput:

   ```bash
   python model_copy_to_br.py \
     -m my-custom-model \
     -s s3://my-bucket/model-path/ \
     -a arn:aws:iam::123456789012:role/MyRole \
     -p 2
   ```

3. Specify custom region and check interval:
   ```bash
   python model_copy_to_br.py \
     -m my-custom-model \
     -s s3://my-bucket/model-path/ \
     -a arn:aws:iam::123456789012:role/MyRole \
     -p 2 \
     -r us-west-2 \
     -i 15
   ```

## Example Output

### Model Creation Only

```
🚀 Creating and monitoring model: my-custom-model
📦 S3 URI: s3://my-bucket/model-path/
🌍 Region: us-east-1
------------------------------------------------------------
📊 Status: CREATING | Elapsed: 00:05:30

✅ SUCCESS! Model 'my-custom-model' is now ACTIVE!
🎉 Total time elapsed: 00:08:45
🔗 Model ARN: arn:aws:bedrock:us-east-1:123456789012:model/my-custom-model
```

### Model Creation with Provisioned Throughput

```
🚀 Creating and monitoring model: my-custom-model
📦 S3 URI: s3://my-bucket/model-path/
🌍 Region: us-east-1
------------------------------------------------------------
📊 Status: CREATING | Elapsed: 00:05:30

✅ SUCCESS! Model 'my-custom-model' is now ACTIVE!
🎉 Total time elapsed: 00:08:45
🔗 Model ARN: arn:aws:bedrock:us-east-1:123456789012:model/my-custom-model

🔄 Setting up provisioned throughput with 2 units...
📊 Provisioned Model Status: CREATING | Elapsed: 00:03:15

✅ SUCCESS! Provisioned model is now ACTIVE!
🎉 Total provisioning time: 00:06:30
🔗 Provisioned Model ARN: arn:aws:bedrock:us-east-1:123456789012:provisioned-model/my-custom-model
```

## Error Handling

The script includes comprehensive error handling for common scenarios:

- Invalid S3 URI format
- Invalid provisioned units value
- Model creation failures
- Provisioned throughput setup failures
- Network connectivity issues

Error messages are clearly displayed with relevant details for troubleshooting.

## Monitoring Progress

The script provides real-time status updates including:

- Current model/provisioned model status
- Elapsed time
- Success/failure notifications
- ARNs for created resources

Progress can be monitored in the terminal, and the script can be interrupted at any time using Ctrl+C.

## Best Practices

1. Always verify the S3 URI is correct and accessible
2. Ensure the IAM role has necessary permissions
3. Start with a single provisioned unit and scale as needed
4. Monitor the AWS console for additional details if errors occur
5. Keep the check interval reasonable (10-15 seconds) to avoid API throttling
