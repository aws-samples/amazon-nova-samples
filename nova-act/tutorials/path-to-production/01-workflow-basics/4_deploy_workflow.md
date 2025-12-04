# Deploying Workflows to Bedrock AgentCore

## Prerequisites
```bash
pip install nova-act boto3
```

- **Docker container runtime** installed and running:
  - Docker Desktop (macOS/Windows)
  - OrbStack (macOS alternative)
  - Finch (open source alternative)
  - Docker Engine (Linux)
- AWS credentials with deployment permissions
- Workflow "getting-started-workflow" created (from example 1)

**Note**: Deployment requires a container runtime to build Docker images. Any Docker-compatible runtime works.

## Overview
This tutorial deploys a workflow to Amazon Bedrock AgentCore Runtime. Deployment packages your code into a container, uploads to ECR, creates IAM roles, and configures the execution environment. After deployment, workflows execute on AWS infrastructure instead of locally.

## Code Walkthrough

### Prerequisites Check
```python
# Check Docker daemon
result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
if result.returncode != 0:
    print("Docker daemon not running")
```
**Explanation**: Verifies Docker is installed and the daemon is running. Deployment requires Docker to build container images. The `docker ps` command tests daemon connectivity.

### Deployment Source Preparation
```python
deploy_dir = tempfile.mkdtemp(prefix="nova-act-deploy-")
workflow_file = os.path.join(deploy_dir, "main.py")  # Must be named main.py

workflow_code = '''from nova_act import NovaAct, workflow

@workflow(workflow_definition_name="getting-started-workflow", model_id="nova-act-latest")
def main(payload):
    with NovaAct(starting_page="https://nova.amazon.com/act", headless=True) as nova:
        result = nova.act("Find the 'Getting Started' section")
        return {"status": "success", "result": result}
'''
```
**Explanation**: Creates a temporary directory with the workflow code in a file named `main.py`. **Important**: 
- The Nova Act CLI requires the entry point file to be named `main.py` for deployment
- **Use `headless=True`** when deploying to AgentCore - containers don't have X server/display, so browser must run in headless mode
- The deployment process packages this directory into a Docker container
- The workflow uses the @workflow decorator to reference the workflow definition created in example 1

### Deployment Execution
```python
subprocess.run(
    ['act', 'workflow', 'deploy', '--name', workflow_name, '--source-dir', source_dir],
    capture_output=True,
    text=True,
    check=True
)
```
**Explanation**: Executes the deployment command. This process:
1. Builds a Docker container with your workflow code
2. Pushes the container image to Amazon ECR
3. Creates an IAM execution role with required permissions
4. Deploys to Bedrock AgentCore Runtime
5. Configures the execution environment

### Deployment Verification
```python
client = boto3.client('nova-act', region_name='us-east-1')
response = client.describe_workflow_definition(
    workflowDefinitionName='getting-started-workflow'
)
```
**Explanation**: Queries the workflow definition to verify deployment succeeded. The response includes the execution role ARN and deployment status. A successful deployment shows status as active.

### Workflow Invocation
```python
# CLI invocation
act workflow invoke --name getting-started-workflow

# Python SDK invocation
client = boto3.client('nova-act', region_name='us-east-1')
response = client.invoke_workflow(
    workflowDefinitionName='getting-started-workflow',
    payload={}
)
```
**Explanation**: Shows two methods to invoke the deployed workflow. CLI invocation is simpler for testing. Python SDK invocation enables programmatic workflow execution from applications. Both execute the workflow on AgentCore infrastructure.

## Running the Example
```bash
# Ensure Docker is running
docker ps

# Run deployment
python 5_workflow_deploy.py
```

Expected output:
```
============================================================
Deployment Prerequisites Check
============================================================

[OK] AWS credentials configured
  Account: 123456789012
[OK] Nova Act CLI available
[OK] Docker available
  Docker version 24.0.0
[OK] Docker daemon running

============================================================
What is Workflow Deployment?
============================================================

Deployment Process:
  • Packages workflow code into Docker container
  • Uploads container image to Amazon ECR
  • Creates IAM execution role with required permissions
  • Deploys to Amazon Bedrock AgentCore Runtime

============================================================
Deploying to Bedrock AgentCore
============================================================

Deploying: getting-started-workflow
  This will take several minutes...
  • Building Docker container
  • Pushing to Amazon ECR
  • Creating IAM execution role
  • Deploying to AgentCore Runtime

✓ Workflow deployed successfully!

============================================================
Verifying Deployment
============================================================

✓ Deployment verified!
  Name: getting-started-workflow
  ARN: arn:aws:nova-act:us-east-1:123456789012:workflow-definition/getting-started-workflow
  Status: ACTIVE
  Execution Role: arn:aws:iam::123456789012:role/NovaActExecutionRole

============================================================
Deployment Complete
============================================================
```

## Troubleshooting

**Missing X server or $DISPLAY error**: Add `headless=True` to NovaAct initialization. AgentCore containers don't have X server, so browser must run in headless mode:
```python
with NovaAct(starting_page="https://example.com", headless=True) as nova:
    # workflow code
```

**Entry point file does not exist**: Ensure your workflow file is named `main.py`. The Nova Act CLI requires this specific filename as the entry point for deployment.

**Docker daemon not running**: Start your container runtime:
- Docker Desktop: Launch the application
- OrbStack: Start OrbStack
- Finch: Run `finch vm start`
- Docker Engine (Linux): Run `sudo systemctl start docker`

**ECR push failed**: Verify AWS credentials have ECR permissions. Check `ecr:CreateRepository`, `ecr:PutImage` permissions.

**Deployment timeout**: Large workflows may take 5-10 minutes. Check CloudWatch logs for build progress.

**IAM role creation failed**: Ensure credentials have `iam:CreateRole` and `iam:AttachRolePolicy` permissions.

## Next Steps
Proceed to `5_invoke_workflow.py` to learn how to invoke deployed workflows using boto3 and use results in downstream processing.
