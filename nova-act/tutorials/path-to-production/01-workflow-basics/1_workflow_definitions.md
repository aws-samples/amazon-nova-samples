# Creating Workflow Definitions in AWS

## Prerequisites
```bash
pip install nova-act boto3
```

- AWS credentials configured
- Nova Act CLI installed

## Overview
This tutorial creates a workflow definition in AWS using the Nova Act CLI. The definition enables logging and tracking when running workflows with AWS authentication. This must be completed before running any other examples in this section.

## Code Walkthrough

### Prerequisites Check
```python
# Check AWS credentials
sts = boto3.client('sts')
identity = sts.get_caller_identity()

# Check Nova Act CLI
subprocess.run(['act', '--version'], capture_output=True, text=True)
```
**Explanation**: Verifies AWS credentials are configured and the Nova Act CLI is installed. The CLI is required to create workflow definitions. AWS credentials must have permissions to create Nova Act resources.

### What are Workflow Definitions?

A workflow definition is an AWS resource that stores workflow configuration. It's not deployed code - it's metadata that enables logging and tracking. When you run workflows locally with AWS IAM authentication, they reference this definition to log execution data to AWS.

**Key characteristics:**
- Created in AWS (not deployed code)
- Stores configuration and logging settings
- Enables tracking of workflow runs
- Allows local execution with AWS logging

**Benefits:**
- Run workflows locally, logs stored in AWS
- Track execution history in Nova Act console
- Centralized monitoring
- No code deployment required for local development

### Creating the Definition
```python
workflow_name = "getting-started-workflow"

subprocess.run(
    ['act', 'workflow', 'create', '--name', workflow_name],
    capture_output=True,
    text=True,
    check=True
)
```
**Explanation**: Uses the Nova Act CLI to create a workflow definition named "getting-started-workflow" in AWS. This command creates the definition in the us-east-1 region by default. The definition is stored in the Nova Act service and can be viewed in the AWS console.

### Verification
```python
# Verify using CLI
result = subprocess.run(
    ['act', 'workflow', 'list'],
    capture_output=True,
    text=True,
    check=True
)

if 'getting-started-workflow' in result.stdout:
    print("✓ Workflow definition verified!")
```
**Explanation**: Lists all workflow definitions to verify creation succeeded. The CLI command queries the Nova Act service and displays all definitions in the current region. This confirms the definition exists and is ready to be referenced by workflows.

## Running the Example

```bash
python 1_workflow_definitions.py
```

**Expected Output:**
```
============================================================
Nova Act Workflow Definitions
============================================================

============================================================
Prerequisites Check
============================================================

[OK] AWS credentials configured
  Account: 975050356504

[OK] Nova Act CLI available
  Version: 1.0.0

============================================================
What are Workflow Definitions?
============================================================

Workflow Definition:
  • Created in AWS (not deployed code)
  • Stores configuration and logging settings
  • Enables tracking of workflow runs
  • Allows local execution with AWS logging

Key Benefits:
  • Run workflows locally, logs stored in AWS
  • Track execution history in Nova Act console
  • Centralized monitoring and observability
  • No code deployment required for local dev

============================================================
Creating Workflow Definition
============================================================

Creating: getting-started-workflow
  This creates the definition in AWS
  Examples 2 and 3 will reference this definition

✓ Workflow definition created!

============================================================
Verifying Workflow Definition
============================================================

✓ Workflow definition verified!
  Name: getting-started-workflow
  Region: us-east-1

============================================================
Next Steps
============================================================

Workflow definition created successfully!

You can now:
  1. Run 2_workflow_decorator.py to use @workflow decorator
  2. Run 3_workflow_context_manager.py for alternative pattern
  3. View workflow runs in Nova Act console

Both examples will reference 'getting-started-workflow'
```

## Key Concepts

**Workflow Definition**: An AWS resource that stores workflow configuration and enables logging. Created once, referenced by multiple workflow runs.

**Local Execution with AWS Logging**: Workflows run on your local machine but log execution data to AWS. This enables centralized monitoring without deploying code.

**AWS IAM Authentication**: When using AWS credentials (instead of API keys), a workflow definition must exist. The workflow references this definition to authenticate and log data.

**CLI vs SDK**: The Nova Act CLI provides commands for managing workflow definitions. The SDK (boto3) is used for invoking workflows and querying execution data.

## Troubleshooting

**CLI not found**: Install with `pip install nova-act`

**Permission denied**: Ensure AWS credentials have `nova-act:CreateWorkflowDefinition` permission

**Definition already exists**: The script handles this gracefully - existing definitions are not overwritten

**Region mismatch**: Workflow definitions are region-specific. Ensure your AWS credentials default to us-east-1 or specify region explicitly

## Next Steps
Run `2_workflow_decorator.py` to use the `@workflow` decorator with this definition.
