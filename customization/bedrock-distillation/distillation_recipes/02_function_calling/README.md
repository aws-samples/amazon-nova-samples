# Function Calling Model Distillation Pipeline

A comprehensive implementation of a three-stage pipeline for distilling knowledge from larger language models into smaller, specialized models for function calling capabilities.

## Overview

This implementation provides a systematic approach to create smaller, efficient models that maintain high-quality function calling capabilities. The pipeline consists of three main stages:
1. Data preparation
2. Model distillation
3. Evaluation

## Notebooks

### 1. Data Preparation (`01_prepare_data.ipynb`)

Prepares training data for function calling model distillation using the Berkeley Function Calling Leaderboard (BFCL) V3 Live dataset:

- **Dataset Features**: 2,251 question-function-answer pairs with diverse scenarios:
  - 258 simple calls
  - 1,053 multiple parameter calls
  - 16 parallel function calls
  - 24 parallel multiple parameter calls
  - 882 irrelevance detection cases
  - 18 relevance detection cases
- **Data Processing**:
  - Implements structured JSON output format for function calls
  - Handles diverse function signatures and parameter types (avg 4 parameters, max 28)
  - Creates training/evaluation splits (50%/50%)
  - Generates mix-in data (10% of training) with ground truth answers
  - Formats data as JSONL for Bedrock distillation service

### 2. Model Distillation (`02_distill.ipynb`)

Implements knowledge transfer using Amazon Bedrock's distillation APIs:

- **Teacher Model**: Nova Premier (us.amazon.nova-premier-v1:0)
- **Student Model**: Nova Lite (amazon.nova-lite-v1:0:300k)
- **Key Features**:
  - Requires custom model deployment for inference
  - Configures IAM roles and S3 buckets for distillation jobs
  - Implements prompt-only and tool configuration approaches
  - Optimized system prompts for function calling capabilities
  - Production-grade monitoring and resource management

### 3. Evaluation (`03_evaluate.ipynb`)

Comprehensive evaluation using the Berkeley Function Calling Leaderboard framework:

- **Evaluation Categories**:
  - Function calling accuracy across multiple test scenarios
  - Irrelevance detection (identifying when no functions are relevant)
  - Live relevance detection (identifying when functions are relevant)
  - Simple and multiple parameter function calls
- **Performance Analysis**:
  - Model-specific performance comparison
  - Accuracy metrics across different test categories
  - Comparative analysis with baseline Nova models
  - Automated scoring using BFCL evaluation framework

## Technical Requirements

### AWS Infrastructure

- Active AWS Account with Bedrock access in supported region (us-east-1 recommended)
- Required IAM roles with permissions for:
  - S3 bucket creation and access
  - Bedrock model customization jobs
  - Model deployment and inference
  - STS assume role capabilities

### Storage Requirements

- S3 bucket for distillation data and outputs
- Local storage for BFCL dataset and processed training files

### Deployment Requirements

- Custom model deployment endpoint for the distilled model
- Python environment with dependencies:
  ```
  boto3
  pandas
  numpy
  bfcl-eval
  PyYAML
  jupyter