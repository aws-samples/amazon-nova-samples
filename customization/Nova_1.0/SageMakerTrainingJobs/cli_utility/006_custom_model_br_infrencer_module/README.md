# Nova Custom Model Inferencer

This module provides a command-line interface for running inference with Amazon Bedrock Nova models, including support for provisioned throughput ARNs and standard model IDs.

## Quick Start

### CLI Command Reference

```bash
# Complete CLI command structure with all possible options

# Run inference using a provisioned throughput ARN
python custom_model_inferencer.py infer \
  --input test.jsonl \
  --output results.jsonl \
  --model-arn "arn:aws:bedrock:us-east-1:123456789012:provisioned-model/model-id" \
  --region us-east-1 \
  --profile my-aws-profile \
  --max-workers 5 \
  --batch-size 20 \
  --max-tokens 2048 \
  --temperature 0.3 \
  --top-p 0.1 \
  --retries 3 \
  --start-index 0 \
  --debug

# Run inference using a standard model ID
python custom_model_inferencer.py infer \
  --input test.jsonl \
  --output results.jsonl \
  --model-id "nova-pro" \
  --max-tokens 2048 \
  --temperature 0.3

# Run inference using a custom model ID
python custom_model_inferencer.py infer \
  --input test.jsonl \
  --output results.jsonl \
  --model-id custom \
  --custom-model-id "us.amazon.custom-model-id:0" \
  --max-tokens 2048

# Validate a JSONL file
python custom_model_inferencer.py validate \
  --input test.jsonl

# Show version information
python custom_model_inferencer.py version
```

### CLI Quick Start

```bash
# Make CLI executable
chmod +x custom_model_inferencer.py

# Run a quick inference with Nova Pro
python custom_model_inferencer.py infer \
  --input test.jsonl \
  --output results.jsonl \
  --model-id nova-pro

# Run inference with a provisioned throughput ARN
python custom_model_inferencer.py infer \
  --input test.jsonl \
  --output results.jsonl \
  --model-arn "arn:aws:bedrock:us-east-1:123456789012:provisioned-model/model-id"

# Validate a JSONL file
python custom_model_inferencer.py validate \
  --input test.jsonl
```

## Table of Contents

- [Overview](#overview)
- [What to Use](#what-to-use)
- [When to Use](#when-to-use)
- [How to Use](#how-to-use)
- [Command Line Interface](#command-line-interface)
- [Examples](#examples)
- [Input Format](#input-format)
- [Output Format](#output-format)
- [Troubleshooting](#troubleshooting)

## Overview

The Nova Custom Model Inferencer provides a command-line interface for running inference with Amazon Bedrock Nova models. It supports:

1. **Standard Model IDs** - Use pre-defined Nova model IDs
2. **Provisioned Throughput ARNs** - Use provisioned throughput for higher performance
3. **Custom Model IDs** - Use custom model IDs for specialized models
4. **Batch Processing** - Process large datasets in batches with parallel execution
5. **Error Handling** - Robust error handling with retry logic and failure tracking

## What to Use

### Supported Models

- **Amazon Nova Micro** (`us.amazon.nova-micro-v1:0`)
- **Amazon Nova Lite** (`us.amazon.nova-lite-v1:0`)
- **Amazon Nova Pro** (`us.amazon.nova-pro-v1:0`)
- **Amazon Nova Premier** (`us.amazon.nova-premier-v1:0`)
- **Custom Models** (specify your own model ID)
- **Provisioned Throughput Models** (specify ARN)

## When to Use

### Use Standard Model IDs When:

- Running inference with standard Nova models
- Testing or development work
- Processing small to medium datasets

### Use Provisioned Throughput ARNs When:

- Running inference at scale
- Need guaranteed throughput
- Processing large datasets
- Production workloads

### Use Custom Model IDs When:

- Working with fine-tuned models
- Using specialized models not in the standard list
- Testing experimental models

## How to Use

The Nova Custom Model Inferencer is used through a command-line interface:

### Installation and Setup

1. **Make the script executable:**

```bash
chmod +x custom_model_inferencer.py
```

2. **Ensure AWS credentials are configured:**

```bash
# Using environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1

# Or using AWS CLI
aws configure
```

3. **Prepare your input data in JSONL format** (see [Input Format](#input-format) section)

### Basic Usage Patterns

#### 1. Run Inference with Standard Model

```bash
python custom_model_inferencer.py infer \
  --input test.jsonl \
  --output results.jsonl \
  --model-id nova-pro
```

#### 2. Run Inference with Provisioned Throughput

```bash
python custom_model_inferencer.py infer \
  --input test.jsonl \
  --output results.jsonl \
  --model-arn "arn:aws:bedrock:us-east-1:123456789012:provisioned-model/model-id"
```

#### 3. Validate Input Data

```bash
python custom_model_inferencer.py validate \
  --input test.jsonl
```

## Command Line Interface

### CLI Commands

#### 1. Infer Command

```bash
python custom_model_inferencer.py infer \
  --input test.jsonl \
  --output results.jsonl \
  --model-id nova-pro \
  --max-tokens 2048 \
  --temperature 0.3
```

**Parameters:**

- `--input`, `-i`: Input JSONL file path (required)
- `--output`, `-o`: Output JSONL file path (required)
- `--model-arn`: ARN for provisioned throughput model (mutually exclusive with --model-id)
- `--model-id`: Model ID - `nova-micro`, `nova-lite`, `nova-pro`, `nova-premier`, or `custom` (mutually exclusive with --model-arn)
- `--custom-model-id`: Custom model ID when --model-id=custom is specified
- `--region`: AWS region (default: us-east-1)
- `--profile`: AWS profile name to use
- `--max-workers`: Maximum number of worker threads (default: 5)
- `--retries`: Maximum number of retries (default: 3)
- `--batch-size`: Number of entries to process before saving results (default: 20)
- `--start-index`: Start processing from this index (default: 0)
- `--max-tokens`: Maximum tokens for generation (default: 2048)
- `--temperature`: Temperature parameter (default: 0.3)
- `--top-p`: Top P parameter (default: 0.1)
- `--debug`: Enable debug logging

#### 2. Validate Command

```bash
python custom_model_inferencer.py validate \
  --input test.jsonl
```

**Parameters:**

- `--input`, `-i`: Input JSONL file path (required)

#### 3. Version Command

```bash
python custom_model_inferencer.py version
```

Shows version information and supported models.

### CLI Examples

#### Basic Inference with Nova Pro

```bash
python custom_model_inferencer.py infer \
  --input test.jsonl \
  --output results.jsonl \
  --model-id nova-pro
```

#### Inference with Provisioned Throughput and Custom Parameters

```bash
python custom_model_inferencer.py infer \
  --input test.jsonl \
  --output results.jsonl \
  --model-arn "arn:aws:bedrock:us-east-1:123456789012:provisioned-model/model-id" \
  --max-tokens 4096 \
  --temperature 0.7 \
  --top-p 0.9 \
  --max-workers 10 \
  --batch-size 50
```

#### Processing Large Files in Batches

```bash
# Process first 1000 entries
python custom_model_inferencer.py infer \
  --input large_file.jsonl \
  --output results_part1.jsonl \
  --model-id nova-pro \
  --batch-size 100 \
  --start-index 0

# Process next 1000 entries
python custom_model_inferencer.py infer \
  --input large_file.jsonl \
  --output results_part2.jsonl \
  --model-id nova-pro \
  --batch-size 100 \
  --start-index 1000
```

#### Using AWS Profile

```bash
python custom_model_inferencer.py infer \
  --input test.jsonl \
  --output results.jsonl \
  --model-id nova-pro \
  --profile my-aws-profile
```

## Input Format

The inferencer expects input files in JSONL format (one JSON object per line) with the following structure:

### Basic Format

```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "text": "What is the capital of France?"
        }
      ]
    }
  ]
}
```

### With System Prompt

```json
{
  "system": [
    {
      "text": "You are a helpful assistant that provides concise answers."
    }
  ],
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "text": "What is the capital of France?"
        }
      ]
    }
  ]
}
```

### Alternative System Prompt Format

```json
{
  "system": "You are a helpful assistant that provides concise answers.",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "text": "What is the capital of France?"
        }
      ]
    }
  ]
}
```

## Output Format

The output is saved in JSONL format with the original input plus additional fields:

```json
{
  "system": [
    {
      "text": "You are a helpful assistant that provides concise answers."
    }
  ],
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "text": "What is the capital of France?"
        }
      ]
    }
  ],
  "model_response": {
    "output": {
      "message": {
        "role": "assistant",
        "content": [
          {
            "text": "Paris is the capital of France."
          }
        ]
      }
    },
    "usage": {
      "inputTokens": 15,
      "outputTokens": 7,
      "totalTokens": 22
    }
  },
  "response_text": "Paris is the capital of France."
}
```

## Troubleshooting

### Common Issues

#### 1. AWS Credentials Not Found

```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Solution:**

- Configure AWS credentials using `aws configure`
- Set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- Use the `--profile` parameter to specify an AWS profile

#### 2. Invalid Model ARN

```
botocore.exceptions.ClientError: An error occurred (ValidationException) when calling the Converse operation: Invalid model ARN
```

**Solution:**

- Check that the ARN format is correct
- Verify that the provisioned throughput model exists and is accessible
- Ensure you have permissions to access the model

#### 3. Input Format Errors

```
Warning on line 5: Missing 'messages' field
```

**Solution:**

- Run the validate command to check your input file: `python custom_model_inferencer.py validate --input test.jsonl`
- Fix any format issues in the input file
- Ensure each line is a valid JSON object with the required fields

#### 4. Rate Limiting

```
botocore.exceptions.ClientError: An error occurred (ThrottlingException) when calling the Converse operation
```

**Solution:**

- Reduce the number of concurrent workers with `--max-workers`
- Use provisioned throughput for higher throughput
- Increase the retry count with `--retries`

### Best Practices

1. **Always validate input files** before running inference
2. **Use batch processing** for large files to avoid memory issues
3. **Save results frequently** by using appropriate batch sizes
4. **Use provisioned throughput** for production workloads
5. **Monitor AWS quotas** to avoid rate limiting
6. **Check failure files** to identify and fix problematic entries

### Getting Help

- **AWS CLI Logs**: Enable debug mode with `--debug` flag
- **Check Failure Files**: Examine `output.jsonl.failures.jsonl` for failed entries
- **AWS Console**: Check CloudWatch logs for API errors
- **AWS Quotas**: Verify Bedrock service quotas in the AWS Console

## Prerequisites

- **AWS Account** with Bedrock access
- **Python 3.7+** with required packages:
  - `boto3`
  - `botocore`
- **AWS Credentials** configured
- **Input Data** in JSONL format

## File Structure

```
SMTJ_nova/006_custom_model_br_infrencer_module/
├── custom_model_inferencer.py  # Main CLI tool
├── README.md                   # This documentation
```
