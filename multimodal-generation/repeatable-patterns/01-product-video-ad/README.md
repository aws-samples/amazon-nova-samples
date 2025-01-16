# Product Advertising Video Use Case with Amazon Nova 

## Introduction

In the rapidly evolving world of digital product marketing, creating high-quality, dynamic video content can be challenging. This notebook demonstrates a comprehensive workflow for generating professional product videos using Amazon Bedrock's image and video generation capabilities. 

This use case focuses on addressing common challenges in product videography using Generative AI, specifically:

1. **Background Transformation**: Replacing product backgrounds seamlessly using outpainting techniques to create visually compelling environments.
2. **Controlled Video Motion**: Generating videos with background movement while keeping the product stationary, ideal for product showcases.
3. **Logo and Text Preservation**: Implementing a frame-by-frame overlay technique to prevent logo and text distortion during video generation.

By combining Amazon Nova Canvas and Amazon Nova Reel, accessed through Amazon Bedrock, we'll walk through a step-by-step process that enables creators and marketers to:

- Dynamically place products in new, imaginative settings
- Create short, engaging product videos
- Maintain brand identity by preserving original product details

This workflow is particularly useful for:
- E-commerce product marketing
- Brand promotional content
- Social media advertising
- Product demonstration videos

This repository includes code examples showing how to create videos for product advertising using both the Nova Canvas image generation model and Nova Reel video generation model. Follow the Jupyter Notebook [01_product_ad_generation.ipynb](01_product_ad_generation.ipynb) step-by-step guide. Sample images for use with this Jupyter Notebook have also been provided.

## Setup - Permissions and Model Entitlement

### Prerequisites

- Your AWS account has been allow-listed for access to the model. See [Access Amazon Bedrock foundation models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) for more information.
- You have the AWS CLI installed.
- You have used the AWS CLI to set the "default" AWS credentials to those associated with your allow-listed account.
- You have Python installed.
- You have a way to run Jupyter Notebooks.

### One-time setup

The following steps only need to be performed once during your initial setup.

#### Add necessary AWS permissions to your user profile

Using Nova Reel requires that you have permissions allowing access to the following AWS Actions:

- "s3:PutObject"
- "bedrock:\*"

Because the code in this notebook and scripts provide some additional conveniences - like creating an S3 bucket and automatically downloading generated video files - you'll need a few additional permissions in order to use them. The required permissions are listed below. If the IAM user you plan to use already has these permissions, there is no need to take any action. Otherwise, attach the following premissions policy to that user in the AWS console. (This guide assumes you know how to apply permissions policies through the console.)

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "NovaReelUserPermissions",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:CreateBucket",
                "s3:ListBucket",
                "bedrock:*"
            ],
            "Resource": "*"
        }
    ]
}
```
