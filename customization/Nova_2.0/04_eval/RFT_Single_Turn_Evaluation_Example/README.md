# Single Turn RFT Evaluation Example

This example demonstrates how to evaluate Amazon Nova models using **Reinforcement Fine-Tuning (RFT) evaluation** with custom reward functions. Learn how to implement AWS Lambda-based reward functions, configure evaluation jobs, and analyze model performance on single-turn tasks.

## Contents

- [RFT_Eval_Example.ipynb](./RFT_Eval_Example.ipynb) - Complete walkthrough for setting up and running RFT evaluation with a custom Lambda reward function. This notebook covers Lambda function creation, dataset preparation, evaluation job execution, and results analysis using a math problem-solving use case.

- [rft_eval_recipe.yaml](./rft_eval_recipe.yaml) - Recipe configuration file for the RFT evaluation job. Defines model parameters, inference settings, and Lambda function integration for the evaluation workflow.

> **📓 Note:** This README provides a high-level overview. **For detailed step-by-step instructions, code examples, and in-depth explanations of each step, please refer to the [RFT_Eval_Example.ipynb](./RFT_Eval_Example.ipynb) notebook.**

## Overview

RFT evaluation enables you to assess model performance using custom reward functions that match your specific task requirements. This example uses an **AWS Lambda function** to evaluate a Nova model's ability to solve algebraic equations with custom scoring logic.

### When to Use Lambda-based RFT Evaluation

- **Single-turn tasks** with custom scoring logic
- Reward computation completes within 15 minutes
- You want AWS to handle the orchestration infrastructure
- Tasks requiring binary or custom reward scoring

### When to Use BYOO (Bring Your Own Orchestrator)

- Multi-turn agent scenarios (e.g., coding agents with iterative debugging)
- Complex reward calculations exceeding 15-minute Lambda timeout
- Custom orchestration logic for simulating realistic environments
- Tasks requiring stateful interactions between model and environment

## Use Case: Math Problem Solving

This example evaluates a Nova model on solving algebraic equations. The Lambda function:
- Parses the model's JSON response to extract the answer
- Compares it against the ground truth
- Returns a binary reward (1.0 for correct, 0.0 for incorrect)
- Tracks additional metrics like format compliance

## Prerequisites

- An AWS account with access to Amazon SageMaker
- Appropriate IAM permissions for SageMaker, Lambda, and S3
- SageMaker execution role with Lambda invocation permissions
- Python environment with `sagemaker==2.254.1` (Nova Forge does not support SageMaker v3)

## Key Configuration Parameters

The recipe file includes important parameters:

- **name**: Evaluation run name (used for output directory naming)
- **model_name_or_path**: Model to evaluate (e.g., `nova-lite-2/prod`)
- **reasoning_effort**: Set to `null`, `low`, or `high` to control reasoning token usage
- **top_logprobs**: Number of tokens with logprobs shown in output (useful for behavior analysis)
- **max_new_tokens**: Maximum tokens to generate (set low for simple tasks like math)
- **reward_lambda_arn**: ARN of your custom Lambda reward function

## Dataset Requirements

RFT evaluation requires JSONL format with the following schema:

```json
{
  "id": "sample_id",
  "messages": [
    {
      "role": "system",
      "content": "System prompt text"
    },
    {
      "role": "user",
      "content": "User query"
    }
  ],
  "reference_answer": {
    "key": "value"
  }
}
```

### Current Limitations

- **Text only**: No multimodal inputs (images, audio, video) supported
- **Single-turn conversations**: Only supports single user message (no multi-turn dialogues)
- **JSON format**: Input data must be in JSONL format (one JSON object per line)
- **Model outputs**: Evaluation performed on generated completions from specified model

## Lambda Function Requirements

### Function Naming
Lambda function name **must** be prefixed with `SageMaker-` (e.g., `SageMaker-RFT-Math-Evaluator`)

### Input Format
```json
[
  {
    "id": "sample_id",
    "messages": [
      {"role": "system", "content": "..."},
      {"role": "user", "content": "..."},
      {"role": "assistant", "content": "..."}
    ],
    "reference_answer": {"key": "value"}
  }
]
```

### Output Format
```json
[
  {
    "id": "sample_id",
    "aggregate_reward_score": 1.0,
    "metrics_list": [
      {
        "name": "correctness",
        "value": 1.0,
        "type": "Reward"
      }
    ]
  }
]
```

## IAM Permissions

The SageMaker execution role requires Lambda invocation permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:<region>:<account-id>:function:SageMaker-RFT-Math-Evaluator"
    }
  ]
}
```

## Evaluation Results

The evaluation job outputs:
- **Aggregated metrics**: Overall performance scores (e.g., correctness, reward scores)
- **Detailed parquet files**: Per-sample results with model responses, predictions, and metrics
- **S3 output**: Results stored in specified S3 location as compressed tar.gz

### Example Metrics
- `lambda_correctness`: Binary correctness score
- `lambda_reward_score`: Aggregate reward score
- Per-sample predictions and ground truth comparisons

## Important Notes

- **SageMaker Version**: Use `sagemaker==2.254.1` - Nova Forge does not support SageMaker v3
- **Lambda Timeout**: Ensure reward computation completes within 15 minutes
- **Region Availability**: Check AWS documentation for supported regions
- **Cost Management**: Remember to clean up resources after evaluation

## Additional Resources

- [Nova RFT Evaluation Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/nova-rft-evaluation.html)
- [Implementing Reward Functions](https://docs.aws.amazon.com/sagemaker/latest/dg/nova-implementing-reward-functions.html)
- [SageMaker Training Jobs](https://docs.aws.amazon.com/sagemaker/latest/dg/train-model.html)
