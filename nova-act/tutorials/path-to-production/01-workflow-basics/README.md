# Workflow Basics

## Purpose
Learn how to create, deploy, and invoke Nova Act workflows on AWS infrastructure. This section covers workflow definitions, execution patterns, deployment to AgentCore, and invocation via boto3.

## Tutorial Sequence

1. **1_workflow_definitions.py**: Creates a workflow definition in AWS using the Nova Act CLI. The definition enables logging and tracking for workflow execution. Creates "getting-started-workflow" that subsequent examples reference.

2. **2_workflow_decorator.py**: Demonstrates the `@workflow` decorator pattern. References the workflow definition from example 1. Runs locally but logs execution data to AWS.

3. **3_workflow_context_manager.py**: Shows the Workflow context manager pattern for managing multiple browser sessions within a single workflow. Alternative to the decorator pattern when you need multiple NovaAct instances.

4. **4_deploy_workflow.py**: Deploys the workflow to Amazon Bedrock AgentCore Runtime. Packages code into Docker containers, uploads to ECR, creates IAM roles, and deploys to AWS infrastructure. After deployment, workflows execute on AWS instead of locally.

5. **5_invoke_workflow.py**: Demonstrates how to invoke deployed workflows using boto3. Shows how to retrieve the AgentCore runtime ARN from deployment state and use the `bedrock-agentcore` client to invoke workflows programmatically.

## Prerequisites
- AWS credentials configured (`aws sts get-caller-identity`)
- Python 3.10+ with nova-act library installed
- Docker installed and running (for deployment)
- Basic knowledge of Python decorators and context managers

## Key Concepts

**Workflow Definition**: An AWS resource that stores workflow configuration. Created once, referenced by multiple workflow runs. Enables logging and tracking without deploying code.

**@workflow Decorator**: Links a Python function to a workflow definition. Enables AWS logging for local execution and prepares the function for deployment.

**Workflow Context Manager**: Alternative to the decorator. Provides explicit control and enables multiple browser sessions within one workflow run.

**AgentCore Deployment**: Packages workflows into Docker containers and deploys to AWS infrastructure. Workflows execute on AWS instead of locally.

**boto3 Invocation**: Programmatic workflow invocation using the `bedrock-agentcore` client. Retrieves runtime ARN from deployment state and calls `invoke_agent_runtime`.

## Execution Flow

```
1. Create Definition (File 1)
   ↓
2. Local Execution with AWS Logging (Files 2-3)
   ↓
3. Deploy to AgentCore (File 4)
   ↓
4. Invoke via boto3 (File 5)
```

## AWS Resources Created

- **Workflow Definition**: Nova Act service resource for configuration
- **Execution Logs**: CloudWatch log groups for execution traces
- **Workflow Artifacts**: S3 storage for detailed logs and artifacts
- **ECR Repository**: Container images (deployment only)
- **IAM Execution Role**: Workflow runtime permissions (deployment only)
- **AgentCore Runtime**: Deployed workflow execution environment (deployment only)

## Pattern Comparison

### @workflow Decorator (File 2)
- Function-based approach
- Single browser session per workflow
- Concise syntax
- Good for simple workflows

### Workflow Context Manager (File 3)
- Explicit configuration control
- Multiple browser sessions per workflow
- More verbose
- Better for complex workflows

## Next Steps

After completing this section, you understand:
- ✓ How to create workflow definitions in AWS
- ✓ How to execute workflows locally with AWS logging
- ✓ How to manage multiple browser sessions
- ✓ How to deploy workflows to AgentCore
- ✓ How to invoke deployed workflows programmatically

You're ready to build production Nova Act workflows on AWS.
