# LLM as a Judge: Customer Feedback Analysis with AWS Bedrock Models

## Overview
This repository contains code for analyzing customer feedback using AWS Bedrock's language models (Nova Pro and Claude Sonnet). The notebook implements a pipeline for thematic analysis of text data, followed by evaluation of the generated themes using newer pre-trained LLMs for an LLM-as-a-judge approach. The end to end LLM-as-a-judge system processes customer comments, extracts themes using an LLM, and then evaluates theme alignment using multiple AI models to represent different personas. 

Amazon Bedrock Nova Premier is Amazon's advanced large language model (LLM) designed specifically for complex reasoning tasks and agentic applications. This sample code demonstrate how to leverage Nova Premier's capabilities to build similar AI as a judge solutions for your next application.

## 🌟 Key Features
- Theme Extraction: Automated analysis of customer feedback
- Multi-Model Analysis: Parallel processing with Nova Premier and Claude
- Statistical Evaluation: Comprehensive inter-rater reliability metrics
- AWS Integration: Seamless S3 and Bedrock API integration
- Real-time Processing: Efficient streaming response handling

## 🛠️ Technical Components

### Models Used
- Amazon Bedrock Nova Pro (`amazon.nova-pro-v1:0` link: https://aws.amazon.com/ai/generative-ai/nova/)
- Anthropic Claude v3.5 Sonnet (`≈` link: https://aws.amazon.com/bedrock/anthropic/)

### Prerequisites
- AWS Account with Bedrock access
- Enabled access to models:
        - amazon.nova-pro-v1:0
        - anthropic.claude-3-5-sonnet-20240620-v1:0
- Python 3.7+
- Dependencies and Key Libraries:
  - `boto3`: AWS SDK
  - `pandas`: Data manipulation
  - `numpy`: Numerical operations
  - `scikit-learn`: Statistical analysis
  - `krippendorff`: Reliability metrics

## 📚 Notebook Contents

### `example.ipynb`
**Model Integration**
   - Multi-model setup
   - Response handling
   - Prompt engineering

### Setup

1. Configure AWS credentials with Amazon Bedrock access
   - Either through AWS CLI: `aws configure`
   - Or by setting environment variables
   - Or by using IAM roles (recommended for SageMaker environments)
   - 
2. Enable Amazon Bedrock models in your AWS account
   - Follow [this link](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html) for instructions on enabling model access

## Usage

1. Start Jupyter Notebook, JupyterLab, or your preferred Jupyter environment.
2. Open any of the sample notebooks and follow the step-by-step instructions within
3. Make sure to update the `region` variable in the notebooks if you're using a region other than `us-east-1`

## Additional Resources
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)

## Important Notes
- These notebooks use Amazon Nova Premier which is billed on an on-demand basis.
- Please review [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) for cost details.
- Amazon Nova Premier supports cross-region inference. Check available regions in the [documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html).
- Sample code is provided for demonstration purposes only and may need adjustments for production use specific to context.