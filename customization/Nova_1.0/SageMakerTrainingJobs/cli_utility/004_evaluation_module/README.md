# Nova Evaluation Module

This document explains the structure of the Nova Evaluation Module, which provides functionality for evaluating Amazon Nova models.

## Overview

The Nova Evaluation Module provides functionality for evaluating Amazon Nova models using various benchmarks and custom datasets through SageMaker Training Jobs. The module has been organized into several Python files, each with a specific responsibility:

1. `__init__.py` - Package initialization and exports
2. `enums_and_configs.py` - Enums and configuration classes
3. `nova_evaluator.py` - Main evaluator class
4. `eval_result_analyzer.py` - Result analysis functionality
5. `helper_functions.py` - Convenience functions
6. `evaluator.py` - Original monolithic implementation (kept for backward compatibility)

## Module Components

### enums_and_configs.py

This module contains all the enum classes and configuration classes used in the evaluation process:

- `ModelType` - Enum for Nova model types (NOVA_MICRO, NOVA_LITE, NOVA_PRO)
- `EvaluationTask` - Enum for evaluation tasks (MMLU, BBH, MATH, etc.)
- `EvaluationStrategy` - Enum for evaluation strategies (ZERO_SHOT, FEW_SHOT, etc.)
- `EvaluationMetric` - Enum for evaluation metrics (ACCURACY, EXACT_MATCH, etc.)
- `RunConfig` - Configuration for evaluation run
- `EvaluationConfig` - Configuration for evaluation task
- `InferenceConfig` - Configuration for model inference

### nova_evaluator.py

This module contains the `NovaEvaluator` class, which is responsible for:

- Creating evaluation recipes for different types of benchmarks
- Running evaluation jobs on SageMaker
- Validating custom datasets
- Managing task-strategy compatibility

### eval_result_analyzer.py

This module contains the `EvalResultAnalyzer` class, which is responsible for:

- Downloading and extracting evaluation outputs from S3
- Getting evaluation metrics from the results
- Accessing raw inference results
- Visualizing TensorBoard logs
- Converting parquet files to JSONL format
- Creating visual failure analysis UIs

### helper_functions.py

This module contains standalone helper functions that provide convenient wrappers around the `NovaEvaluator` class methods:

- `create_text_evaluation_job` - Create and run text benchmark evaluation job
- `create_custom_dataset_evaluation_job` - Create and run custom dataset evaluation job

## Usage Examples

### Basic Evaluation

```python
# Import directly from the module files
from nova_evaluator import NovaEvaluator
from enums_and_configs import ModelType, EvaluationTask
from helper_functions import create_text_evaluation_job
import sagemaker

# Initialize SageMaker session
sagemaker_session = sagemaker.Session()
role = "arn:aws:iam::123456789012:role/SageMakerRole"

# Create evaluator
evaluator = NovaEvaluator(sagemaker_session=sagemaker_session, role=role)

# Run text benchmark evaluation
estimator = create_text_evaluation_job(
    evaluator=evaluator,
    job_name="nova-mmlu-eval",
    model_type=ModelType.NOVA_LITE,
    model_path="amazon.nova-lite-v1:0:300k",
    task=EvaluationTask.MMLU,
    output_s3_uri="s3://my-bucket/output/",
    subtask="high_school_mathematics"
)
```

### Analyzing Results

```python
# Import directly from the module file
from eval_result_analyzer import EvalResultAnalyzer
import sagemaker

# Initialize SageMaker session
sagemaker_session = sagemaker.Session()

# Create analyzer
analyzer = EvalResultAnalyzer(sagemaker_session=sagemaker_session)

# Download and extract output
extract_dir = analyzer.download_and_extract_output("nova-mmlu-eval-2025-06-25-12-34-56")

# Get metrics
metrics = analyzer.get_metrics("nova-mmlu-eval-2025-06-25-12-34-56", extract_dir)
print(metrics)

# Visualize TensorBoard logs
tensorboard_dir = analyzer.get_tensorboard_logs("nova-mmlu-eval-2025-06-25-12-34-56", extract_dir)
analyzer.visualize_tensorboard(tensorboard_dir)
```

## Command Line Interface

The module provides a command-line interface:

`nova_eval_cli.py` - A CLI that follows the same pattern as other Nova modules like nova-tunner.py and nova-data-prep.py

### Basic Usage

```bash
# Make the script executable (if not already)
chmod +x nova_eval_cli.py

# Run directly from the module directory
./nova_eval_cli.py text-benchmark --help
./nova_eval_cli.py multimodal --help
./nova_eval_cli.py custom-dataset --help
```

### Examples

```bash
# Text benchmark evaluation
./nova_eval_cli.py text-benchmark --job-name "nova-micro-mmlu-eval" --model-type micro \
  --model-path "amazon.nova-micro-v1:0:300k" --task mmlu --subtask high_school_mathematics \
  --output-s3-uri "s3://my-bucket/eval-results/" --wait

# Custom dataset evaluation
./nova_eval_cli.py custom-dataset --job-name "custom-eval" --model-type lite \
  --model-path "s3://my-bucket/fine-tuned-model/" \
  --dataset-s3-uri "s3://my-bucket/custom-dataset/gen_qa.jsonl" \
  --output-s3-uri "s3://my-bucket/eval-results/" --wait

# Validate a dataset
./nova_eval_cli.py validate-dataset --dataset-path "./gen_qa.jsonl"

# Analyze evaluation results
./nova_eval_cli.py analyze-results --job-name "nova-micro-mmlu-eval-2025-06-25-09-30-45" \
  --metrics --raw-inferences --convert-parquet --visual-failure-analysis
```

### Command Reference

The `nova_eval_cli.py` provides a comprehensive interface with all the functionality using the modular structure:

#### Text Benchmark Evaluation

```bash
python nova_eval_cli.py text-benchmark \
  --job-name "nova-micro-mmlu-eval" \
  --model-type micro \
  --model-path "amazon.nova-micro-v1:0:300k" \
  --task mmlu \
  --subtask high_school_mathematics \
  --output-s3-uri "s3://my-bucket/eval-results/" \
  --max-tokens 4096 \
  --temperature 0.0 \
  --top-p 1.0 \
  --top-k -1 \
  --wait
```

#### Multimodal Benchmark Evaluation

```bash
python nova_eval_cli.py multimodal \
  --job-name "nova-pro-mmmu-eval" \
  --model-type pro \
  --model-path "amazon.nova-pro-v1:0:300k" \
  --subtask physics \
  --dataset-s3-uri "s3://my-bucket/mmmu-dataset/" \
  --output-s3-uri "s3://my-bucket/eval-results/" \
  --wait
```

#### Custom Dataset Evaluation

```bash
# Standard custom dataset evaluation with gen_qa format
python nova_eval_cli.py custom-dataset \
  --job-name "custom-eval" \
  --model-type lite \
  --model-path "s3://my-bucket/fine-tuned-model/" \
  --dataset-s3-uri "s3://my-bucket/custom-dataset/gen_qa.jsonl" \
  --output-s3-uri "s3://my-bucket/eval-results/" \
  --max-tokens 12000 \
  --wait

# Custom dataset evaluation with Bedrock Conversation Format conversion
python nova_eval_cli.py custom-dataset \
  --job-name "bedrock-format-eval" \
  --model-type lite \
  --model-path "s3://my-bucket/fine-tuned-model/" \
  --dataset-s3-uri "s3://my-bucket/custom-dataset/bedrock_format.jsonl" \
  --output-s3-uri "s3://my-bucket/eval-results/" \
  --is-bedrock-format \
  --max-tokens 12000 \
  --wait
```

#### Dataset Validation

```bash
# Validate a dataset
python nova_eval_cli.py validate-dataset \
  --dataset-path "./gen_qa.jsonl"

# Validate a dataset in Bedrock Conversation Format
python nova_eval_cli.py validate-dataset \
  --dataset-path "./test.jsonl" \
  --is-bedrock-format
```

#### List Available Subtasks

```bash
python nova_eval_cli.py list-subtasks \
  --task mmlu
```

#### Create Recipe Only

```bash
python nova_eval_cli.py create-recipe \
  --job-name "test-recipe" \
  --model-type micro \
  --model-path "nova-micro/prod" \
  --task mmlu \
  --subtask mathematics \
  --output "my_recipe.yaml" \
  --show
```

#### Analyze Evaluation Results

```bash
# Basic analysis
python nova_eval_cli.py analyze-results \
  --job-name "nova-micro-mmlu-eval-2025-06-25-09-30-45" \
  --output-uri "s3://my-bucket/eval-results/nova-micro-mmlu-eval-2025-06-25-09-30-45/output.tar.gz"

# Get metrics and save to file
python nova_eval_cli.py analyze-results \
  --job-name "nova-micro-mmlu-eval-2025-06-25-09-30-45" \
  --metrics \
  --save-metrics "metrics.json"

# Get raw inferences and convert parquet to JSONL
python nova_eval_cli.py analyze-results \
  --job-name "nova-micro-mmlu-eval-2025-06-25-09-30-45" \
  --raw-inferences \
  --convert-parquet \
  --output-jsonl "./inferences.jsonl"

# Create visual failure analysis UI
python nova_eval_cli.py analyze-results \
  --job-name "nova-micro-mmlu-eval-2025-06-25-09-30-45" \
  --raw-inferences \
  --convert-parquet \
  --visual-failure-analysis \
  --ui-port 8888

# Visualize TensorBoard logs
python nova_eval_cli.py analyze-results \
  --job-name "nova-micro-mmlu-eval-2025-06-25-09-30-45" \
  --tensorboard \
  --visualize \
  --port 8080
```

### Comprehensive CLI Commands

The modular CLI includes all the functionality of the original CLI:

1. `text-benchmark` - Run text benchmark evaluation
2. `multimodal` - Run multimodal benchmark evaluation
3. `custom-dataset` - Run custom dataset evaluation
4. `validate-dataset` - Validate custom dataset format
5. `list-subtasks` - List available subtasks for a task
6. `create-recipe` - Create evaluation recipe without running job
7. `analyze-results` - Analyze evaluation results

The `analyze-results` command includes several options:

- `--metrics` - Get evaluation metrics
- `--save-metrics` - Save metrics to file
- `--raw-inferences` - Get raw inference results
- `--convert-parquet` - Convert parquet files to JSONL format
- `--output-jsonl` - Path to save the converted JSONL file
- `--visual-failure-analysis` - Create a visual UI for analyzing failures
- `--tensorboard` - Get TensorBoard logs
- `--visualize` - Visualize TensorBoard logs
- `--port` - Port for TensorBoard server
- `--ui-port` - Port for visual failure analysis UI server

## Backward Compatibility

The original monolithic implementation files are kept in the `old/` directory for reference. New code should use the modular structure for better organization and maintainability.
