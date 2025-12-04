# Workflow Decorator Pattern

## Prerequisites
```bash
pip install nova-act boto3
```

- Completed `1_workflow_definitions.py`
- Workflow "getting-started-workflow" created in AWS
- AWS credentials configured

## Overview
This tutorial demonstrates using the `@workflow` decorator to reference workflow definitions created in AWS. The decorator enables production deployment and AWS logging for local execution.

## Code Walkthrough

### Workflow Decorator Usage
```python
@workflow(workflow_definition_name="getting-started-workflow", model_id="nova-act-latest")
def search_documentation_workflow():
    """References the workflow definition from 1_workflow_definitions.py."""
    with NovaAct(starting_page="https://nova.amazon.com/act") as nova:
        result = nova.act("Find and return the main heading text on this page")
        return result
```
**Explanation**: The `@workflow` decorator references an existing workflow definition in AWS. The `workflow_definition_name` must match the definition created in example 1. When this function executes locally, logs are automatically sent to AWS. This enables centralized monitoring without deploying code.

### Decorator Parameters
```python
@workflow(workflow_definition_name="getting-started-workflow", model_id="nova-act-latest")
```
**Explanation**: Two parameters are required:
- `workflow_definition_name`: References the AWS workflow definition (must already exist)
- `model_id`: Specifies which Nova Act model to use

The workflow definition was created in example 1. The decorator links this function to that definition, enabling AWS logging and deployment readiness.

### Main Function Pattern
```python
def main(payload):
    """Main function required for production workflow deployment."""
    result = search_documentation_workflow()
    return result

if __name__ == "__main__":
    main({})
```
**Explanation**: Production workflows require a `main()` function that accepts a `payload` parameter. This enables parameterized execution when deployed to AWS. For local testing, an empty payload `{}` is passed. When deployed, the payload contains input data from the invocation.

## Running the Example

```bash
python 2_workflow_decorator.py
```

**Expected Output:**
```
============================================================
Workflow Decorator Pattern for Production Deployment
============================================================

============================================================
Workflow Decorator Pattern
============================================================

[OK] The @workflow decorator enables production deployment
  Automatically references workflow definition in AWS
  Enables deployment to AWS infrastructure
  Provides AWS logging for local execution

→ Next: Defining a workflow function with @workflow decorator

[OK] Executing workflow: getting-started-workflow
  Model: nova-act-latest
  Execution: Local with AWS logging

Executing workflow with AWS logging...

Workflow Result: Nova Act

✓ Completed: Workflow executed successfully

Execution Details:
  • Workflow ran locally on your machine
  • Logs automatically stored in AWS
  • Execution tracked in Nova Act console

============================================================
View Your Workflow Logs
============================================================

[INFO] Your workflow execution has been logged to AWS

To view logs and execution details:
  1. Open Nova Act Console:
     https://us-east-1.console.aws.amazon.com/nova-act/home
  2. Click on 'getting-started-workflow'
  3. View the latest workflow run
  4. Explore execution traces, logs, and artifacts

What you'll see in the console:
  • Workflow run status and duration
  • Step-by-step execution trace
  • Location of detailed logs and artifacts
  • Session and act-level metrics

============================================================
Decorator Parameters Explained
============================================================

@workflow Parameters:
  • workflow_definition_name: References the AWS workflow definition
  • model_id: Specifies the Nova Act model version

Workflow Definition:
  • References the definition created in file 1
  • Enables AWS logging for local execution
  • Provides deployment readiness

============================================================
Main Function Pattern
============================================================

[OK] Production workflows require a main() function
  • main() must accept a payload parameter
  • Enables parameterized workflow execution
  • Required for AWS deployment compatibility

→ Next: Executing workflow through main() function

============================================================
Workflow Decorator Complete
============================================================

✓ Completed: @workflow decorator pattern demonstrated
→ Next: Learn Workflow context manager alternative

Key Takeaways:
1. @workflow decorator enables AWS logging for local execution
2. Logs stored in AWS, viewable in Nova Act console
3. Workflow definition enables deployment readiness
4. Local execution with AWS tracking and monitoring

Next Tutorial:
Run: python 3_workflow_context_manager.py
```

## Key Concepts

**@workflow Decorator**: Links a Python function to an AWS workflow definition. Enables AWS logging for local execution and prepares the function for deployment.

**Workflow Definition Reference**: The `workflow_definition_name` parameter must match an existing definition in AWS. This was created in example 1.

**Local Execution with AWS Logging**: The workflow runs on your local machine but sends logs to AWS. This provides centralized monitoring without deploying code.

**Main Function**: Required for deployment. Accepts a `payload` parameter that contains input data when the workflow is invoked in AWS.

**Model ID**: Specifies which Nova Act model version to use. `nova-act-latest` uses the newest available model.

## Troubleshooting

**Workflow definition not found**: Run `1_workflow_definitions.py` first to create the definition

**AWS credentials error**: Ensure credentials are configured with `aws configure`

**Import error**: Verify `nova-act` is installed with `pip install nova-act`

**Logs not appearing**: Check AWS console after a few minutes - logs may take time to appear

## Next Steps
Run `3_workflow_context_manager.py` to learn the Workflow context manager pattern for managing multiple browser sessions.
