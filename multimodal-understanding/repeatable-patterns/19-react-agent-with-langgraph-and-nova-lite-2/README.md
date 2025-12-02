# Amazon Nova Lite 2.0 Agent Samples

## Overview

Amazon Bedrock Nova Lite 2.0 is Amazon's new large language model (LLM) designed specifically for complex reasoning tasks and agentic applications. This sample code demonstrate how to leverage Nova Lite's capabilities with popular agent frameworks to build sophisticated AI solutions.

## Notebook

### Academic Paper Analysis with LangGraph ReAct Pattern

**Filename:** `01_ReAct_Agent_with_LangGraph.ipynb`

This notebook implements a LangGraph ReAct agent that can analyze academic papers (PDF files) using Amazon Nova Lite 2.0. The agent has specific tools to:

- Load and parse PDF documents
- Summarize papers
- Extract research questions
- Extract key results and findings
- Identify research gaps and future work

Key features:
- LangGraph implementation of the ReAct pattern
- PDF text extraction and section parsing
- Structured JSON outputs for research analysis
- Step-by-step reasoning

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
- [LangGraph Documentation](https://www.langchain.com/langgraph)

## Important Notes

- These notebooks use Amazon Nova Lite 2.0 which is billed on an on-demand basis. Please review [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) for cost details.
- Amazon Nova Lite 2.0 supports cross-region inference. Check available regions in the [documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html).
- Sample code is provided for demonstration purposes and may need adjustments for production use.