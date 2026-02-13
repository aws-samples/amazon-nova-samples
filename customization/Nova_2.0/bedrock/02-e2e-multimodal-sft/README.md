# Fine-tuning Amazon Nova Lite for Document Extraction

This folder contains a step-by-step notebook workflow for fine-tuning Amazon Nova Lite to extract structured data from scanned W2 tax forms. It covers baseline evaluation, data preparation, fine-tuning on Amazon Bedrock, deployment, and post-training evaluation.

## Notebooks

| # | Notebook | Description |
|---|----------|-------------|
| 1 | [01_base_model_eval.ipynb](./01_base_model_eval.ipynb) | Download the W2 tax form dataset, upload images to S3, and evaluate the base Nova Lite model on 100 test samples to establish a baseline accuracy. |
| 2 | [02_data_preparation.ipynb](./02_data_preparation.ipynb) | Format ground-truth data into Bedrock conversation-schema JSONL, upload datasets to S3, and create the IAM role and policy required for fine-tuning. |
| 3 | [03_finetune_on_bedrock.ipynb](./03_finetune_on_bedrock.ipynb) | Submit a model customization job on Bedrock, monitor training progress, and visualize step-wise training loss. |
| 4 | [04_deploy_on_bedrock.ipynb](./04_deploy_on_bedrock.ipynb) | Create an on-demand deployment of the fine-tuned model and verify it with a sample inference. |
| 5 | [05_eval_custom_model.ipynb](./05_eval_custom_model.ipynb) | Evaluate the fine-tuned model on 100 test samples, compare accuracy against the base model, and clean up AWS resources. |

## Supporting Files

| File | Description |
|------|-------------|
| `util.py` | Shared helper functions used across all notebooks (AWS client setup, S3 uploads, dataset formatting, evaluation logic, IAM resource management, cleanup). |

## Prerequisites

- An AWS account with access to Amazon Bedrock for Amazon Nova Lite
- Appropriate IAM permissions for Bedrock, S3, and IAM role creation
- Python environment with required libraries (`boto3`, `datasets`, `pandas`, `matplotlib`, `deepdiff`, `pillow`, `tqdm`)

## Results

The fine-tuned model achieves **91.13%** overall field extraction accuracy compared to **51.90%** for the base model, a **+39.22 percentage point** improvement.

| Category | Base Model | Fine-tuned | Improvement |
|----------|-----------|------------|-------------|
| Employee Information | 60.00% | 92.67% | +32.67% |
| Employer Information | 48.00% | 84.33% | +36.33% |
| Earnings | 42.57% | 88.71% | +46.14% |
| Benefits | 50.00% | 100.00% | +50.00% |
| Multi-State Employment | 62.91% | 93.68% | +30.77% |

## Important Notes

- On-demand inferencing for custom Nova models is currently available in `us-east-1`
- Fine-tuning jobs for multi-modal models may take several hours to complete
- Run the notebooks in order; each notebook persists variables for the next via `%store`
- Remember to run the cleanup cell in notebook 05 to delete the deployment and IAM resources

## Data Source

This project uses a synthetic W2 tax form dataset: [Fake W-2 (US Tax Form) Dataset](https://www.kaggle.com/datasets/mcvishnu1/fake-w2-us-tax-form-dataset/data) (CC0 License).
