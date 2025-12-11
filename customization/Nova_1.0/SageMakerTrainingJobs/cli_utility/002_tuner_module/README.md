# Nova Fine-tuning Runner (Step 2)

This module provides the `nova-tunner.py` script for running Nova model fine-tuning jobs on SageMaker. It is typically used as Step 2 in the Nova fine-tuning process, after preparing your training data.

## Prerequisites

Before using this script, you should have:

1. Training and validation data files in JSONL format, either:
   - Already in S3 (if you're skipping Step 1)
   - Created using `nova-data-prep.py` (Step 1)
2. AWS credentials configured with appropriate permissions
3. Either a custom recipe YAML file OR use the auto-recipe selection feature

## Recipe Selection Methods

The script supports **two ways** to specify training recipes:

### Method 1: Custom Recipe YAML (Traditional)

Provide your own recipe YAML file with custom configurations.

### Method 2: Auto-Select from Repository (New)

Automatically select the appropriate recipe based on model type and training method.

## Usage Patterns

### 1. Auto-Select Recipe (Recommended for Standard Training)

**When to use**: When you want to use standard, tested recipes for common training scenarios.

#### SFT (Supervised Fine-Tuning) - Full Rank

```bash
python nova-tunner.py \
  --job-name my-sft-job \
  --model-name lite \
  --training-type sft \
  --data-jsonl s3://my-bucket/train.jsonl \
  --validation-jsonl s3://my-bucket/val.jsonl
```

#### LoRA (Low-Rank Adaptation) Training

```bash
python nova-tunner.py \
  --job-name my-lora-job \
  --model-name micro \
  --training-type lora \
  --data-jsonl s3://my-bucket/train.jsonl \
  --validation-jsonl s3://my-bucket/val.jsonl
```

#### DPO (Direct Preference Optimization) - Full Rank

```bash
python nova-tunner.py \
  --job-name my-dpo-job \
  --model-name pro \
  --training-type dpo \
  --data-jsonl s3://my-bucket/train.jsonl \
  --validation-jsonl s3://my-bucket/val.jsonl
```

#### DPO+SFT (LoRA DPO) Training

```bash
python nova-tunner.py \
  --job-name my-dpo-sft-job \
  --model-name lite \
  --training-type dpo-sft \
  --data-jsonl s3://my-bucket/train.jsonl \
  --validation-jsonl s3://my-bucket/val.jsonl
```

### 2. Custom Recipe YAML

**When to use**: When you need custom configurations, experimental settings, or specific hyperparameters not covered by standard recipes.

```bash
python nova-tunner.py \
  --job-name custom-job \
  --model-name lite \
  --data-jsonl s3://my-bucket/train.jsonl \
  --validation-jsonl s3://my-bucket/val.jsonl \
  --recipe-yaml recipes/my_custom_recipe.yaml
```

### 3. Custom Recipe Repository Path

**When to use**: When you have your own recipe repository or want to use recipes from a different location.

```bash
python nova-tunner.py \
  --job-name custom-repo-job \
  --model-name micro \
  --training-type lora \
  --recipe-repo-path /path/to/my/recipes \
  --data-jsonl s3://my-bucket/train.jsonl
```

### 4. Upload Local Files and Train

**When to use**: When you have local JSONL files that need to be uploaded to S3.

```bash
# With auto-selected recipe
python nova-tunner.py \
  --job-name local-upload-job \
  --model-name lite \
  --training-type sft \
  --data-jsonl local_train.jsonl \
  --validation-jsonl local_val.jsonl \
  --upload-data

# With custom recipe
python nova-tunner.py \
  --job-name local-custom-job \
  --model-name lite \
  --data-jsonl local_train.jsonl \
  --validation-jsonl local_val.jsonl \
  --recipe-yaml recipes/my_recipe.yaml \
  --upload-data
```

### 5. Dry Run for Configuration Validation

**When to use**: To test your configuration without starting an actual training job.

```bash
# Test auto-selected recipe
python nova-tunner.py \
  --job-name test-job \
  --model-name lite \
  --training-type sft \
  --data-jsonl s3://my-bucket/train.jsonl \
  --dry-run

# Test custom recipe
python nova-tunner.py \
  --job-name test-job \
  --model-name lite \
  --data-jsonl s3://my-bucket/train.jsonl \
  --recipe-yaml recipes/my_recipe.yaml \
  --dry-run
```

## Training Type Guide

### When to Use Each Training Type:

| Training Type | Use Case                | Description                                                         | Resource Requirements        |
| ------------- | ----------------------- | ------------------------------------------------------------------- | ---------------------------- |
| **sft**       | General fine-tuning     | Full-rank supervised fine-tuning for comprehensive model adaptation | High (full model parameters) |
| **lora**      | Efficient fine-tuning   | Low-rank adaptation for parameter-efficient training                | Medium (reduced parameters)  |
| **dpo**       | Preference optimization | Direct preference optimization for alignment training               | High (full model parameters) |
| **dpo-sft**   | Efficient preference    | LoRA-based DPO for parameter-efficient preference optimization      | Medium (reduced parameters)  |

### Model Size Recommendations:

| Model     | Use Case                                      | Training Time | Resource Cost |
| --------- | --------------------------------------------- | ------------- | ------------- |
| **micro** | Experimentation, prototyping, small datasets  | Fastest       | Lowest        |
| **lite**  | Production applications, balanced performance | Medium        | Medium        |
| **pro**   | High-performance applications, large datasets | Slowest       | Highest       |

## Recipe Auto-Selection Details

When using `--training-type`, the script automatically selects recipes from:

```
NovaPrimeRecipesStaging/sagemaker_training_job_recipes/recipes/
├── supervised-fine-tuning/smtj_ga/nova/
│   ├── nova_micro_p5_gpu_sft.yaml          # --training-type sft --model-name micro
│   ├── nova_lite_p5_gpu_sft.yaml           # --training-type sft --model-name lite
│   ├── nova_pro_p5_gpu_sft.yaml            # --training-type sft --model-name pro
│   ├── nova_micro_p5_gpu_lora_sft.yaml     # --training-type lora --model-name micro
│   ├── nova_lite_p5_gpu_lora_sft.yaml      # --training-type lora --model-name lite
│   └── nova_pro_p5_gpu_lora_sft.yaml       # --training-type lora --model-name pro
└── direct-preference-ptimization/smtj_ga/nova/
    ├── nova_micro_p5_gpu_dpo.yaml          # --training-type dpo --model-name micro
    ├── nova_lite_p5_gpu_dpo.yaml           # --training-type dpo --model-name lite
    ├── nova_pro_p5_gpu_dpo.yaml            # --training-type dpo --model-name pro
    ├── nova_micro_p5_gpu_lora_dpo.yaml     # --training-type dpo-sft --model-name micro
    ├── nova_lite_p5_gpu_lora_dpo.yaml      # --training-type dpo-sft --model-name lite
    └── nova_pro_p5_gpu_lora_dpo.yaml       # --training-type dpo-sft --model-name pro
```

## Advanced Configuration

### Recipe Overrides with Auto-Selected Recipes

You can combine auto-selection with custom overrides:

```bash
# Auto-select SFT recipe but override learning rate and epochs
python nova-tunner.py \
  --job-name sft-custom \
  --model-name lite \
  --training-type sft \
  --data-jsonl s3://my-bucket/train.jsonl \
  --recipe-override "optimizer.learning_rate=0.001,training.epochs=5"

# Auto-select LoRA recipe but modify LoRA parameters
python nova-tunner.py \
  --job-name lora-custom \
  --model-name micro \
  --training-type lora \
  --data-jsonl s3://my-bucket/train.jsonl \
  --recipe-override "lora_config.rank=16,lora_config.alpha=32"
```

## Parameters

### Required Parameters

- `--job-name`: Name for the SageMaker training job
- `--model-name`: Model type to use (micro, lite, or pro)
- `--data-jsonl`: Path to training data file (local or S3)

### Recipe Selection Parameters (Choose One)

- `--recipe-yaml`: Path to custom recipe YAML file
- `--training-type`: Auto-select recipe type (sft, lora, dpo, dpo-sft)

### Optional Parameters

- `--validation-jsonl`: Path to validation data file (local or S3)
- `--recipe-repo-path`: Custom path to recipe repository (used with --training-type)
- `--upload-data`: Flag to upload local files to S3
- `--role`: IAM role ARN for SageMaker (auto-detected if not provided)
- `--s3-bucket`: S3 bucket for data and outputs (uses default if not provided)
- `--max-run`: Maximum runtime in seconds (default: 432000 = 5 days)
- `--hyperparameters`: Additional hyperparameters (format: key1=value1,key2=value2)
- `--recipe-override`: Override specific recipe values (format: key1.key2=value1,key3.key4=value2)
- `--dry-run`: Validate configuration without starting training job
- `--verbose`: Enable verbose output

### Parameter Combinations

| Scenario               | Required Parameters                                             | Optional Parameters                                             |
| ---------------------- | --------------------------------------------------------------- | --------------------------------------------------------------- |
| **Auto-select recipe** | `--job-name`, `--model-name`, `--data-jsonl`, `--training-type` | `--validation-jsonl`, `--recipe-repo-path`, `--recipe-override` |
| **Custom recipe**      | `--job-name`, `--model-name`, `--data-jsonl`, `--recipe-yaml`   | `--validation-jsonl`, `--recipe-override`                       |
| **Upload local data**  | Add `--upload-data` to either scenario above                    | Same as above                                                   |

## Common Scenarios

### 1. After Using nova-data-prep.py (Step 1)

If you've used `nova-data-prep.py` to prepare your data, it will have created properly formatted files in S3. Use those S3 paths directly:

```bash
python nova-tunner.py \
  --job-name continuation-job \
  --model-name lite \
  --data-jsonl s3://my-bucket/prepared_train.jsonl \
  --validation-jsonl s3://my-bucket/prepared_val.jsonl \
  --recipe-yaml recipes/my_recipe.yaml
```

### 2. Using Your Own Data Files

If you have your own properly formatted JSONL files in S3:

```bash
python nova-tunner.py \
  --job-name custom-data-job \
  --model-name lite \
  --data-jsonl s3://my-bucket/custom_train.jsonl \
  --validation-jsonl s3://my-bucket/custom_val.jsonl \
  --recipe-yaml recipes/my_recipe.yaml
```

### 3. Using Recipe Overrides

You can override specific values in your recipe YAML file directly from the command line. Here are common examples:

#### Modifying Training Parameters

```bash
# Adjust learning rate and epochs
python nova-tunner.py \
  --job-name training-test \
  --model-name lite \
  --data-jsonl s3://my-bucket/train.jsonl \
  --recipe-yaml recipes/my_recipe.yaml \
  --recipe-override "optimizer.learning_rate=0.001,training.epochs=5"

# Change batch size and gradient accumulation
python nova-tunner.py \
  --job-name batch-test \
  --model-name lite \
  --data-jsonl s3://my-bucket/train.jsonl \
  --recipe-yaml recipes/my_recipe.yaml \
  --recipe-override "training.batch_size=4,training.gradient_accumulation_steps=4"
```

#### Adjusting LoRA Configuration

```bash
# Modify LoRA rank and alpha
python nova-tunner.py \
  --job-name lora-test \
  --model-name lite \
  --data-jsonl s3://my-bucket/train.jsonl \
  --recipe-yaml recipes/my_recipe.yaml \
  --recipe-override "lora_config.rank=16,lora_config.alpha=32,lora_config.dropout=0.2"
```

#### Mixed Value Types

```bash
# Example using different value types
python nova-tunner.py \
  --job-name mixed-test \
  --model-name lite \
  --data-jsonl s3://my-bucket/train.jsonl \
  --recipe-yaml recipes/my_recipe.yaml \
  --recipe-override "training.use_fp16=true,optimizer.name=adamw,training.epochs=3"
```

The recipe override feature supports:

- Nested keys using dots (e.g., `optimizer.learning_rate`, `lora_config.rank`)
- Multiple overrides in one command (comma-separated)
- Value types:
  - Numbers: integers (1, 2, 3) and floats (0.001, 1.5)
  - Booleans: true/false
  - Strings: optimizer names, model types, etc.

Common override paths:

```
optimizer.learning_rate     # Adjust learning rate
optimizer.name             # Change optimizer type
training.epochs           # Number of training epochs
training.batch_size       # Batch size
training.gradient_accumulation_steps  # Gradient accumulation
lora_config.rank         # LoRA rank
lora_config.alpha        # LoRA alpha
lora_config.dropout      # LoRA dropout rate
training.use_fp16        # Enable/disable mixed precision
```

### 4. Testing Different Model Types

Try different model sizes based on your needs:

```bash
# For smaller datasets or faster iteration
python nova-tunner.py \
  --job-name micro-test \
  --model-name micro \
  --data-jsonl s3://my-bucket/train.jsonl \
  --recipe-yaml recipes/my_recipe.yaml

# For production-grade models
python nova-tunner.py \
  --job-name pro-production \
  --model-name pro \
  --data-jsonl s3://my-bucket/train.jsonl \
  --recipe-yaml recipes/my_recipe.yaml
```

## Error Handling

The script performs several validations:

1. Verifies that S3 files exist before starting the job
2. Validates required parameters are provided
3. Checks file permissions and AWS credentials
4. Provides clear error messages for common issues

If you encounter errors:

1. Check that your data files exist in the specified S3 locations
2. Verify your AWS credentials and permissions
3. Ensure your recipe YAML file is properly formatted
4. Use the `--verbose` flag for more detailed error information

## Next Steps

After your training job completes successfully:

1. Check the model manifest at the output path
2. Review TensorBoard logs for training metrics
3. The model will be ready for deployment or further evaluation

For more advanced usage and customization options, refer to the recipe YAML documentation and SageMaker documentation.
