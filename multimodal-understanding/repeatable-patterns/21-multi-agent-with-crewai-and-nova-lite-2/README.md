# Amazon Nova Lite 2.0 Agent Samples

## Overview

Amazon Bedrock Nova Lite 2.0 is Amazon's new large language model (LLM) designed specifically for complex reasoning tasks and agentic applications. This sample code demonstrate how to leverage Nova Premier's capabilities with popular agent frameworks to build sophisticated AI solutions.

## Notebook

### Multi-Agent Content Creation with CrewAI

**Filename:** `01_Multi_Agent_with_CrewAI.ipynb`

This notebook demonstrates using CrewAI with Amazon Bedrock Nova Lite 2.0 to create a content creation pipeline with multiple specialized agents working together:

- Content Researcher: Finds relevant information on topics
- Content Writer: Creates engaging content based on research
- Content Editor: Optimizes content for impact and SEO

Key features:
- Multi-agent collaboration
- Custom tools for each agent role
- Sequential workflow processing
- Tool delegation between agents
- Web-search

## Prerequisites

To run these notebooks, you'll need:

1. An AWS account with access to Amazon Bedrock
2. Amazon Bedrock model access enabled for Nova Lite 2.0 (model ID: `us.amazon.nova-2-lite-v1:0`)
3. Proper AWS credentials configured
4. Python 3.10+ with Jupyter Notebook or JupyterLab installed

## Setup

1. Configure AWS credentials with Amazon Bedrock access
   - Either through AWS CLI: `aws configure`
   - Or by setting environment variables
   - Or by using IAM roles (recommended for SageMaker environments)

## Usage

1. Start Jupyter Notebook, JupyterLab or your preferred Jupyter environment.

2. Open any of the sample notebooks and follow the step-by-step instructions within

3. Make sure to update the `region` variable in the notebooks if you're using a region other than `us-east-1`

## Additional Resources

- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [CrewAI Documentation](https://docs.crewai.com/introduction)

## Important Notes

- These notebooks use Amazon Nova Lite 2.0 which is billed on an on-demand basis. Please review [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) for cost details.
- Amazon Nova Lite 2.0 supports cross-region inference. Check available regions in the [documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html).
- Sample code is provided for demonstration purposes and may need adjustments for production use.