# Fine-tuning Amazon Nova Lite for Document OCR/Extraction

This repository demonstrates how to fine-tune Amazon Nova Lite models for specialized OCR tasks, specifically focusing on extracting structured data from scanned W2 tax forms. Learn how to prepare multi-modal training data, fine-tune a custom model, and evaluate its performance on tax document extraction tasks.

## Contents

- [01_data_preparation.ipynb](./01_data_preparation.ipynb) - Prepare data for fine-tuning Amazon Nova Lite with OCR capabilities. This notebook covers processing a dataset of W2 tax form images, uploading them to S3, creating properly formatted prompts, and preparing the training, validation, and test datasets according to the Bedrock conversation schema.

- [02_finetune_on_bedrock.ipynb](./02_finetune_on_bedrock.ipynb) - Fine-tune the Amazon Nova Lite multi-modal model on Amazon Bedrock. This notebook covers creating a fine-tuning job with appropriate hyperparameters, monitoring job progress, visualizing training metrics, creating a deployment for the fine-tuned model, and testing with inference on sample images.

- [03_evaluate_custom_models.ipynb](./03_evaluate_custom_models.ipynb) - Evaluate and compare the base and fine-tuned models. This notebook provides a comprehensive benchmarking framework that measures extraction accuracy across different field categories (employee information, employer information, earnings, etc.), analyzes error patterns, and quantifies the improvements achieved through fine-tuning.

## Prerequisites

- An AWS account with access to Amazon Bedrock for Amazon Nova Lite model
- Appropriate IAM permissions for Bedrock, S3, and IAM role creation
- A working SageMaker or Python environment with required libraries (boto3, pandas, matplotlib, etc.)

## Use Case

Automated extraction of information from tax documents presents unique challenges due to the critical importance of accuracy, especially for numerical values. This project demonstrates how fine-tuning can significantly improve the accuracy of OCR models on domain-specific documents like W2 tax forms.

The fine-tuned model achieves 85.31% overall field extraction accuracy compared to 55.87% for the base model, representing a substantial 29.44% improvement.

## Important Notes

- Custom Nova model On-demand inferencing deployment is currently available in the us-east-1 AWS region
- Fine-tuning jobs for multi-modal models may take several hours to complete
- The synthetic W2 tax form dataset contains 2,000 images
- Remember to clean up AWS resources after evaluation to avoid unnecessary costs

## Data Sources

This project uses a synthetic dataset of W2 tax forms [Fake W-2 (US Tax Form) Dataset
](https://www.kaggle.com/datasets/mcvishnu1/fake-w2-us-tax-form-dataset/data) under CC0 License.