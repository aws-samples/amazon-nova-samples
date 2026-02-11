# Utils Package

A utility package for converting Hugging Face datasets to RFT (Rejection Fine-Tuning) format, uploading to Amazon S3, and deploying AWS Lambda functions.

## Features

- **HF to RFT Conversion**: Convert Hugging Face datasets to RFT format
- **S3 Upload**: Upload files to Amazon S3 with progress tracking
- **Lambda Deployment**: Create and manage AWS Lambda functions with layer support
- **IAM Role Management**: Create and configure IAM roles for Lambda execution
- **Batch Operations**: Process multiple dataset splits and upload directories
- **Error Handling**: Comprehensive error handling and validation

## Installation

### Prerequisites

```bash
# Install required packages
pip install boto3 datasets
```

### AWS Configuration

Configure your AWS credentials:

```bash
# Using AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

## Quick Start

### 1. Convert HF Dataset to RFT Format

```python
from datasets import load_dataset
from utils import parse_hf_dataset

# Load dataset
ds = load_dataset('your-dataset-name')

# Convert to RFT format
parse_hf_dataset(ds, 'rft_data.jsonl', split='train')
```

### 2. Upload to S3

```python
from utils import upload_to_s3

# Upload file
s3_uri = upload_to_s3(
    file_path='rft_data.jsonl',
    bucket_name='my-bucket',
    s3_key='datasets/rft_data.jsonl',
    region='us-east-1'
)

print(f"Uploaded to: {s3_uri}")
```

### 3. Complete Pipeline

```python
from datasets import load_dataset
from utils import parse_hf_dataset, upload_to_s3

# Load and convert
ds = load_dataset('your-dataset-name')
parse_hf_dataset(ds, 'output.jsonl', split='train')

# Upload to S3
s3_uri = upload_to_s3(
    file_path='output.jsonl',
    bucket_name='my-bucket',
    s3_key='rft-datasets/output.jsonl'
)
```

## API Reference

### parse_hf_to_rft Module

#### `parse_hf_dataset(dataset, output_file, split='train')`

Convert Hugging Face dataset to RFT format.

**Parameters:**

- `dataset`: Hugging Face dataset object
- `output_file` (str): Path to output JSONL file
- `split` (str): Dataset split to use (default: 'train')

**Example:**

```python
from datasets import load_dataset
from utils import parse_hf_dataset

ds = load_dataset('codeparrot/apps', split='train[:100]')
parse_hf_dataset(ds, 'rft_train.jsonl', split='train')
```

**Input Format:**
The dataset should have this structure:

```python
{
    'question': 'Write a function that adds two numbers',
    'info': '{"tests": "{\"inputs\": [\"1, 2\"], \"outputs\": [\"3\"]}"}'
}
```

**Output Format:**

```json
{
  "messages": [
    { "role": "user", "content": "Write a function that adds two numbers" }
  ],
  "reference_answer": {
    "inputs": ["1, 2"],
    "outputs": ["3"]
  }
}
```

#### `parse_and_split_dataset(dataset, output_prefix='rft_data', split='train', train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, shuffle=True, seed=42)`

Parse HF dataset and automatically split it into train/validation/test sets, creating three separate JSONL files. This function is ideal for preparing data that will be uploaded to S3 for training.

**Parameters:**

- `dataset`: Hugging Face dataset object
- `output_prefix` (str): Prefix for output files (default: 'rft_data')
- `split` (str): Dataset split to use from input (default: 'train')
- `train_ratio` (float): Ratio of data for training (default: 0.8)
- `val_ratio` (float): Ratio of data for validation (default: 0.1)
- `test_ratio` (float): Ratio of data for testing (default: 0.1)
- `shuffle` (bool): Whether to shuffle before splitting (default: True)
- `seed` (int): Random seed for reproducibility (default: 42)

**Returns:** Dictionary with file paths: `{'train': 'path', 'val': 'path', 'test': 'path'}`

**Example:**

```python
from datasets import load_dataset
from utils import parse_and_split_dataset, upload_to_s3

# Load and split dataset
dataset = load_dataset('your-dataset-name')
files = parse_and_split_dataset(
    dataset,
    output_prefix='rft_data',
    train_ratio=0.8,
    val_ratio=0.1,
    test_ratio=0.1
)

# Upload all splits to S3
bucket_name = 'my-training-bucket'
for split_name, file_path in files.items():
    s3_uri = upload_to_s3(
        file_path=file_path,
        bucket_name=bucket_name,
        s3_key=f'rft-datasets/{split_name}.jsonl'
    )
    print(f"✓ {split_name}: {s3_uri}")
```

---

### s3_uploader Module

#### `upload_to_s3(file_path, bucket_name, s3_key=None, region=None, public_read=False, metadata=None, show_progress=True)`

Upload a file to S3 with additional options.

**Parameters:**

- `file_path` (str): Local file path
- `bucket_name` (str): S3 bucket name
- `s3_key` (str, optional): S3 object key (uses filename if not provided)
- `region` (str, optional): AWS region
- `public_read` (bool): Make file publicly readable (default: False)
- `metadata` (dict, optional): Custom metadata
- `show_progress` (bool): Show upload progress (default: True)

**Returns:** S3 URI (str)

**Example:**

```python
from utils import upload_to_s3

s3_uri = upload_to_s3(
    file_path='data.jsonl',
    bucket_name='my-bucket',
    s3_key='datasets/data.jsonl',
    region='us-east-1',
    metadata={'version': '1.0'}
)
```

#### `upload_file_to_s3(file_path, bucket_name, s3_key, region=None, extra_args=None, show_progress=True)`

Lower-level function for uploading files with full control.

**Parameters:**

- `file_path` (str): Local file path
- `bucket_name` (str): S3 bucket name
- `s3_key` (str): S3 object key
- `region` (str, optional): AWS region
- `extra_args` (dict, optional): Extra S3 upload arguments
- `show_progress` (bool): Show upload progress

**Example:**

```python
from utils import upload_file_to_s3

s3_uri = upload_file_to_s3(
    file_path='data.jsonl',
    bucket_name='my-bucket',
    s3_key='data.jsonl',
    extra_args={
        'StorageClass': 'STANDARD_IA',
        'ServerSideEncryption': 'AES256'
    }
)
```

#### `upload_directory_to_s3(directory_path, bucket_name, s3_prefix='', region=None, file_pattern='*', show_progress=True)`

Upload all files from a directory to S3.

**Parameters:**

- `directory_path` (str): Local directory path
- `bucket_name` (str): S3 bucket name
- `s3_prefix` (str): S3 key prefix (folder path)
- `region` (str, optional): AWS region
- `file_pattern` (str): Glob pattern to filter files (default: '\*')
- `show_progress` (bool): Show upload progress

**Returns:** List of S3 URIs

**Example:**

```python
from utils import upload_directory_to_s3

s3_uris = upload_directory_to_s3(
    directory_path='./data',
    bucket_name='my-bucket',
    s3_prefix='datasets',
    file_pattern='*.jsonl'
)
```

#### `verify_s3_file_exists(bucket_name, s3_key, region=None)`

Check if a file exists in S3.

**Returns:** bool

**Example:**

```python
from utils import verify_s3_file_exists

exists = verify_s3_file_exists('my-bucket', 'data.jsonl')
print(f"File exists: {exists}")
```

#### `get_s3_file_info(bucket_name, s3_key, region=None)`

Get information about an S3 object.

**Returns:** Dictionary with file information

**Example:**

```python
from utils import get_s3_file_info

info = get_s3_file_info('my-bucket', 'data.jsonl')
print(f"Size: {info['size']} bytes")
print(f"Last Modified: {info['last_modified']}")
```

---

### lambda_deployer Module

#### `create_lambda_function(lambda_script_path, function_name, role_arn, handler='lambda_function.lambda_handler', runtime='python3.11', timeout=300, memory_size=512, environment_variables=None, layers=None, description='', region='us-east-1', skip_if_exists=False)`

Create or update an AWS Lambda function from a Python script.

**Parameters:**

- `lambda_script_path` (str): Path to the Python script file
- `function_name` (str): Name for the Lambda function
- `role_arn` (str): IAM role ARN with Lambda execution permissions
- `handler` (str): Handler function in format "filename.function_name" (default: "lambda_function.lambda_handler")
- `runtime` (str): Python runtime version (default: "python3.11")
- `timeout` (int): Function timeout in seconds (default: 300)
- `memory_size` (int): Memory allocation in MB (default: 512)
- `environment_variables` (dict, optional): Dictionary of environment variables
- `layers` (list, optional): List of Lambda layer ARNs
- `description` (str, optional): Function description
- `region` (str): AWS region (default: "us-east-1")
- `skip_if_exists` (bool): Skip update if function exists (default: False)

**Returns:** Function ARN (str)

**Example:**

```python
from utils import create_lambda_function

# Create Lambda with layers
arn = create_lambda_function(
    lambda_script_path="reward_lambda.py",
    function_name="my-reward-function",
    role_arn="arn:aws:iam::123456789012:role/lambda-execution-role",
    layers=[
        "arn:aws:lambda:us-east-1:123456789012:layer:numpy:1",
        "arn:aws:lambda:us-east-1:123456789012:layer:pandas:2"
    ],
    timeout=600,
    memory_size=1024
)
```

#### `update_lambda_layers(function_name, layers, region='us-east-1')`

Update the Lambda layers for an existing function without modifying its code.

**Parameters:**

- `function_name` (str): Name of the Lambda function to update
- `layers` (list): List of Lambda layer ARNs to attach (empty list removes all layers)
- `region` (str): AWS region (default: "us-east-1")

**Returns:** Updated Lambda configuration (dict)

**Example:**

```python
from utils import update_lambda_layers

# Add layers to existing function
update_lambda_layers(
    function_name="my-reward-function",
    layers=[
        "arn:aws:lambda:us-east-1:123456789012:layer:numpy:1",
        "arn:aws:lambda:us-east-1:123456789012:layer:custom-deps:3"
    ]
)

# Remove all layers
update_lambda_layers(
    function_name="my-reward-function",
    layers=[]
)
```

#### `create_lambda_with_dependencies(lambda_script_path, function_name, role_arn, dependencies_dir=None, **kwargs)`

Create Lambda function including a directory of dependencies.

**Parameters:**

- `lambda_script_path` (str): Path to the Python script file
- `function_name` (str): Name for the Lambda function
- `role_arn` (str): IAM role ARN with Lambda execution permissions
- `dependencies_dir` (str, optional): Path to directory containing dependencies
- `**kwargs`: Additional arguments passed to create_lambda_function

**Returns:** Function ARN (str)

**Example:**

```python
from utils import create_lambda_with_dependencies

arn = create_lambda_with_dependencies(
    lambda_script_path="lambda_function.py",
    function_name="my-function",
    role_arn="arn:aws:iam::123456789012:role/lambda-role",
    dependencies_dir="./python/site-packages",
    timeout=600
)
```

#### `delete_lambda_function(function_name, region='us-east-1')`

Delete an AWS Lambda function.

**Parameters:**

- `function_name` (str): Name of the Lambda function to delete
- `region` (str): AWS region (default: "us-east-1")

**Returns:** bool (True if successful)

**Example:**

```python
from utils import delete_lambda_function

success = delete_lambda_function("my-function")
```

#### `get_lambda_info(function_name, region='us-east-1')`

Get information about an AWS Lambda function.

**Parameters:**

- `function_name` (str): Name of the Lambda function
- `region` (str): AWS region (default: "us-east-1")

**Returns:** Lambda function configuration (dict)

**Example:**

```python
from utils import get_lambda_info

info = get_lambda_info("my-function")
print(f"Runtime: {info['Configuration']['Runtime']}")
print(f"Memory: {info['Configuration']['MemorySize']}MB")
```

---

### lambda_role_helper Module

#### `create_lambda_execution_role(role_name, managed_policies=None, region='us-east-1')`

Create an IAM role that can be assumed by Lambda with necessary permissions.

**Parameters:**

- `role_name` (str): Name for the IAM role
- `managed_policies` (list, optional): List of managed policy ARNs to attach
- `region` (str): AWS region (default: "us-east-1")

**Returns:** Role ARN (str)

**Example:**

```python
from utils import create_lambda_execution_role

role_arn = create_lambda_execution_role(
    role_name="my-lambda-role",
    managed_policies=[
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
    ]
)
```

#### `get_or_create_lambda_role(role_name='lambda-execution-role', managed_policies=None, region='us-east-1')`

Get an existing Lambda execution role or create one if it doesn't exist.

**Parameters:**

- `role_name` (str): Name for the IAM role
- `managed_policies` (list, optional): List of managed policy ARNs to attach
- `region` (str): AWS region (default: "us-east-1")

**Returns:** Role ARN (str)

**Example:**

```python
from utils import get_or_create_lambda_role

role_arn = get_or_create_lambda_role(
    role_name="lambda-execution-role",
    managed_policies=[
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    ]
)
```

## Usage Examples

### Example 1: Process Multiple Splits

```python
from datasets import load_dataset
from utils import parse_hf_dataset, upload_to_s3

dataset = load_dataset('your-dataset-name')
bucket_name = 'my-training-bucket'

for split in ['train', 'validation', 'test']:
    if split in dataset:
        # Convert to RFT
        output_file = f'rft_{split}.jsonl'
        parse_hf_dataset(dataset, output_file, split=split)

        # Upload to S3
        s3_uri = upload_to_s3(
            file_path=output_file,
            bucket_name=bucket_name,
            s3_key=f'rft-datasets/{split}.jsonl'
        )
        print(f"✓ {split}: {s3_uri}")
```

### Example 2: Upload with Metadata

```python
from utils import upload_to_s3

s3_uri = upload_to_s3(
    file_path='rft_data.jsonl',
    bucket_name='my-bucket',
    s3_key='datasets/rft_data.jsonl',
    metadata={
        'source': 'huggingface',
        'format': 'rft',
        'version': '1.0',
        'created_by': 'data-pipeline'
    }
)
```

### Example 3: Production Pipeline with Error Handling

```python
from datasets import load_dataset
from utils import parse_hf_dataset, upload_to_s3, verify_s3_file_exists

try:
    # Load and convert
    dataset = load_dataset('your-dataset-name')
    parse_hf_dataset(dataset, 'output.jsonl', split='train')

    # Upload to S3
    s3_uri = upload_to_s3(
        file_path='output.jsonl',
        bucket_name='my-bucket',
        s3_key='datasets/output.jsonl'
    )

    # Verify upload
    if verify_s3_file_exists('my-bucket', 'datasets/output.jsonl'):
        print(f"✓ Successfully uploaded to {s3_uri}")

except Exception as e:
    print(f"Error: {e}")
```

## Error Handling

The package includes comprehensive error handling:

- `S3UploadError`: Raised for S3 upload failures
- `FileNotFoundError`: Raised when local file doesn't exist
- `ValueError`: Raised for invalid parameters

**Example:**

```python
from utils import upload_to_s3, S3UploadError

try:
    s3_uri = upload_to_s3('file.jsonl', 'my-bucket', 'data/file.jsonl')
except S3UploadError as e:
    print(f"Upload failed: {e}")
except FileNotFoundError:
    print("File not found")
```

## Requirements

- Python 3.7+
- boto3
- datasets (Hugging Face)

## Troubleshooting

### AWS Credentials Not Found

```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

### Permission Denied

Ensure your IAM user/role has the following permissions:

- `s3:PutObject`
- `s3:GetObject`
- `s3:ListBucket`

### Dataset Format Issues

Ensure your dataset has the required structure:

- `question` field with the problem description
- `info` field (JSON string) containing `tests` (also JSON string) with `inputs` and `outputs`

## More Examples

See `example_usage.py` for comprehensive examples including:

- Basic conversion and upload
- Multiple splits processing
- Advanced S3 options
- Directory uploads
- Verification and file info
- Production pipelines with error handling

## License

MIT License

## Contributing

Contributions welcome! Please ensure your code follows the existing style and includes appropriate tests.
