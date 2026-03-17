# Evaluate generative AI models with an Amazon Nova rubric-based LLM judge on Amazon SageMaker AI

This project demonstrates how to use Amazon Nova's rubric-based LLM-as-a-Judge methodology to evaluate and compare outputs from different large language models using Amazon SageMaker Training Jobs.

## Overview

The Amazon Nova rubric-based LLM-as-a-Judge approach uses a powerful language model to evaluate the quality of responses from other models by dynamically generating custom evaluation rubrics for each comparison. This project compares responses from a **Qwen2.5 1.5B Instruct model (Model A)** against a **Qwen2.5 7B Instruct model (Model B)**, both deployed on SageMaker AI.

## Key Features

- **Objective Comparison**: Systematic evaluation using automatically generated, context-specific rubrics with weighted criteria (accuracy, completeness, clarity, etc.)
- **Scalable Assessment**: Automated rubric generation and criterion-based scoring across large datasets without manual rubric design
- **Detailed Metrics**: Win rates, confidence intervals, preference distributions, weighted scores per criterion, and detailed justifications for each evaluation dimension
- **Cost-Effective**: More efficient than human evaluation for large-scale comparisons while maintaining evaluation transparency through explicit rubric criteria
- **Adaptive Evaluation**: Rubrics are tailored to each specific question-answer pair, ensuring relevant and context-appropriate assessment criteria

## Project Structure

```
Final Files/
├── Amazon-Nova-Rubric-Based-LLM-as-a-Judge-Sagemaker-AI.ipynb  # Main notebook with complete workflow
├── deploy_model_arg.py                             # Script to deploy HuggingFace models to SageMaker
├── eval_rubric_judge_recipe.yaml                   # Configuration for rubric-based evaluation
├── llm_judge.jsonl                                 # Dataset with prompts and model responses
└── evaluation_metrics.png                          # Visualization of evaluation results
```

## Prerequisites

- AWS Account with SageMaker and Bedrock access
- Appropriate IAM roles and permissions
- SageMaker Studio or Jupyter environment

## Files Description

### 1. Amazon-Nova-Rubric-Based-LLM-as-a-Judge-Sagemaker-AI.ipynb
Main Jupyter notebook that walks through the complete evaluation workflow, including model deployment, response generation, and rubric-based evaluation using Amazon Nova.

### 2. deploy_model_arg.py
Python script for deploying HuggingFace models to SageMaker endpoints.

**Usage:**
```bash
python deploy_model_arg.py <model_name>
```

**Features:**
- Deploys models using HuggingFace LLM container (version 3.0.1)
- Uses ml.g5.12xlarge instances
- Implements least outstanding requests routing strategy
- Auto-generates endpoint names from model names

### 3. eval_rubric_judge_recipe.yaml
Configuration file for the rubric-based LLM judge evaluation.

**Key Parameters:**
- Model: `amazon.nova-2-lite-v1:0:256k`
- Task: `rubric_llm_judge`
- Strategy: `judge`
- Max new tokens: 15000
- Temperature: 0 (deterministic output)

### 4. llm_judge.jsonl
Dataset containing prompts and responses from both models for evaluation. Each line contains:
- `prompt`: The question or task
- `response_A`: Output from Qwen2.5 1.5B Instruct model
- `response_B`: Output from Qwen2.5 7B Instruct model

### 5. evaluation_metrics.png
Visual representation of the evaluation results showing comparative metrics between the two models.

## Getting Started

1. Open `Amazon-Nova-Rubric-Based-LLM-as-a-Judge-Sagemaker-AI.ipynb` in SageMaker Studio or Jupyter
2. Follow the notebook cells to:
   - Deploy models using the deployment script
   - Generate responses from both models
   - Run rubric-based evaluation using Amazon Nova
   - Analyze results and metrics

## Model Deployment

Deploy models to SageMaker endpoints:

```bash
python deploy_model_arg.py Qwen/Qwen2.5-1.5B-Instruct
python deploy_model_arg.py Qwen/Qwen2.5-7B-Instruct
```

## Evaluation Process

The evaluation uses Amazon Nova to:
1. Generate custom rubrics for each prompt-response pair
2. Score responses based on multiple criteria (accuracy, completeness, clarity, etc.)
3. Provide detailed justifications for each evaluation
4. Calculate aggregate metrics including win rates and confidence intervals

## Results

Model B (Qwen2.5 7B Instruct) demonstrates superior performance with a 70% win rate against Model A (Qwen2.5 1.5B Instruct), though there's notable variability across different question types.

### Aggregate Statistics

- **Total Evaluations**: 11 (7 detailed datapoints provided)
- **Valid Judgments**: 10 (excluding 1 inference error)
- **Win Distribution**: Model B scored 7 wins vs Model A's 3 wins
- **Preference Rate**: 70% preferred B, 30% preferred A
- **95% Confidence Interval**: [0.400, 0.909] - indicating statistical confidence in B's superiority
- **Error Rate**: 9.1% (1 inference error out of 11 evaluations)

### Performance Analysis

**Model B Wins (3 cases - 60% of detailed evaluations)**
- Notre Dame student newspapers: Provided more accurate, complete information with specific examples
- Common Sense publication year: Correctly identified 1916 vs Model A's incorrect 1879
- Notre Dame's oldest structure: Accurately identified western facade and southern spire

**Model A Wins (2 cases - 40% of detailed evaluations)**
- Congregation of Holy Cross headquarters: Correctly explained decentralized structure vs Model B's inaccurate single location claim
- Primary seminary information: Provided detailed, accurate explanation vs Model B's completely unrelated content

### Weighted Performance Metrics

- **Average Weighted Score A**: 0.495
- **Average Weighted Score B**: 0.630
- **Average Margin (B-A)**: -0.135 (negative indicates B's advantage)

The 70% win rate with a confidence interval not crossing the 50% threshold suggests statistically meaningful superiority for the 7B model, though the relatively small sample size (11 evaluations) means continued testing would strengthen these conclusions.

## Visualization

To help practitioners quickly interpret the outcome of a Nova LLM-as-a-Judge evaluation, the project includes a comprehensive visualization function (`plot_nova_judge_results`) that produces a single image summarizing key metrics across six panels:

1. **Score Distribution Bar Chart** – Shows preference counts for Model A, Model B, ties, and inference errors, providing an immediate sense of evaluation decisiveness
2. **Win Rate with 95% Confidence Interval** – Plots Model B's overall win rate with error bars reflecting confidence bounds. A vertical reference line at 50% marks no preference; intervals not crossing this line indicate statistical significance
3. **Preference Pie Chart** – Visually displays the proportion of preferences among valid judgments for quick distribution understanding
4. **A vs. B Score Comparison** – Side-by-side bar chart comparing raw preference counts with annotated margin of difference
5. **Win Rate Gauge** – Semicircular gauge depicting Model B's win rate on a 0-100% scale, ideal for nontechnical stakeholders
6. **Summary Statistics Table** – Compact table compiling total evaluations, error counts, win rate, and confidence intervals for easy reference

The visualization is generated using Matplotlib and Seaborn, and can be saved, displayed in Jupyter notebooks, or embedded in documentation. See `evaluation_metrics.png` for the complete visual representation of results.

## Conclusion

This project demonstrates a complete Amazon Nova Rubric-Based LLM-as-a-Judge evaluation pipeline using Amazon SageMaker AI. The methodology provides:

- **Scalable Evaluation**: Automated rubric-based comparison of multiple models with dynamically generated evaluation criteria
- **Statistical Rigor**: Confidence intervals and significance testing with weighted scoring across multiple rubric dimensions (accuracy, completeness, clarity)
- **Cost Efficiency**: Reduced need for human evaluation through automated rubric generation and criterion-specific scoring
- **Actionable Insights**: Clear metrics for model selection with detailed justifications per evaluation criterion and weighted performance analysis

The evaluation results demonstrate that larger model size (7B vs 1.5B parameters) generally correlates with better performance, achieving a statistically significant 70% win rate. However, the smaller model showed competitive performance on specific question types, particularly those requiring nuanced understanding of organizational structures.

## License

This project uses AWS services and follows AWS service terms and conditions.
