#!/usr/bin/env python3
"""
Deploying Workflows to Bedrock AgentCore

This script demonstrates how to deploy a workflow to Amazon Bedrock AgentCore Runtime.
Deployment packages your code into a container, uploads to ECR, and creates execution infrastructure.

Prerequisites:
- Completed 3_workflow_context_manager.py
- Workflow "getting-started-workflow" created in AWS
- AWS credentials with deployment permissions
- Nova Act CLI installed: pip install nova-act
- Docker installed and running

Setup:
1. Ensure Docker is running
2. Run this script to deploy workflow to AgentCore
3. Workflow will execute on AWS infrastructure instead of locally

Note: Deployment creates ECR repositories, IAM roles, and AgentCore resources.
"""

import boto3
import subprocess
import os


def check_prerequisites():
    """Check prerequisites for deployment."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mDeployment Prerequisites Check\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"\033[93m[OK]\033[0m AWS credentials configured")
        print(f"  Account: {identity['Account']}")
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m AWS credentials not configured: {e}")
        return False
    
    # Check Nova Act CLI
    try:
        result = subprocess.run(['act', '--version'], capture_output=True, text=True)
        print(f"\033[93m[OK]\033[0m Nova Act CLI available")
    except FileNotFoundError:
        print(f"\033[91m[ERROR]\033[0m Nova Act CLI not found")
        print("  Install with: pip install nova-act")
        return False
    
    # Check Docker
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        print(f"\033[93m[OK]\033[0m Docker available")
        print(f"  {result.stdout.strip()}")
        
        # Check if Docker daemon is running
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"\033[91m[ERROR]\033[0m Docker daemon not running")
            print("  Start Docker Desktop or Docker daemon")
            return False
        print(f"\033[93m[OK]\033[0m Docker daemon running")
    except FileNotFoundError:
        print(f"\033[91m[ERROR]\033[0m Docker not found")
        print("  Install from: https://docs.docker.com/get-docker/")
        return False
    
    return True


def explain_deployment():
    """Explain what deployment does."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mWhat is Workflow Deployment?\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[38;5;214mDeployment Process:\033[0m")
    print("  • Packages workflow code into Docker container")
    print("  • Uploads container image to Amazon ECR")
    print("  • Creates IAM execution role with required permissions")
    print("  • Deploys to Amazon Bedrock AgentCore Runtime")
    print("  • Configures execution environment and resources")
    
    print(f"\n\033[38;5;214mAfter Deployment:\033[0m")
    print("  • Workflow executes on AWS infrastructure (not locally)")
    print("  • Scalable and managed execution environment")
    print("  • Integrated with AWS services (S3, CloudWatch, etc.)")
    print("  • Production-ready with monitoring and logging")


def create_deployment_source():
    """Create source directory with workflow code for deployment."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mPreparing Deployment Source\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    # Create temporary deployment directory
    import tempfile
    deploy_dir = tempfile.mkdtemp(prefix="nova-act-deploy-")
    
    # Create workflow file
    workflow_file = os.path.join(deploy_dir, "main.py")
    workflow_code = '''import nova_act
from nova_act import NovaAct, workflow
import logging

logger = logging.getLogger(__name__)

@workflow(workflow_definition_name="getting-started-workflow", model_id="nova-act-latest")
def main(payload):
    """Deployed workflow that runs on AgentCore."""
    logger.info(f"Nova Act version: {nova_act.__version__}")
    logger.info(f"Nova Act package location: {nova_act.__file__}")
    
    with NovaAct(starting_page="https://nova.amazon.com/act/gym/next-dot/", headless=True) as nova:
        result = nova.act("Click explore destinations and find the cheapest trip")
        return {"status": "success", "result": result}

if __name__ == "__main__":
    main({})
'''
    
    with open(workflow_file, 'w') as f:
        f.write(workflow_code)
    
    print(f"\033[93m[OK]\033[0m Created deployment source")
    print(f"  Directory: {deploy_dir}")
    print(f"  Workflow: main.py")
    
    return deploy_dir


def deploy_workflow(source_dir):
    """Deploy workflow to Bedrock AgentCore."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mDeploying to Bedrock AgentCore\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    workflow_name = "getting-started-workflow"
    
    print(f"\n\033[38;5;214mDeploying: {workflow_name}\033[0m")
    print("  This will take several minutes...")
    print("  • Building Docker container")
    print("  • Pushing to Amazon ECR")
    print("  • Creating IAM execution role")
    print("  • Deploying to AgentCore Runtime")
    
    try:
        # Use .act venv's act CLI to avoid mise conflicts
        act_cli = os.path.join(os.path.dirname(__file__), '..', '.act', 'bin', 'act')
        
        result = subprocess.run(
            [act_cli, 'workflow', 'deploy', '--name', workflow_name, '--source-dir', source_dir],
            text=True,
            check=True
        )
        print(f"\n\033[92m✓ Workflow deployed successfully!\033[0m")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n\033[91m[ERROR]\033[0m Deployment failed")
        return False


def verify_deployment():
    """Verify workflow is deployed and ready."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mVerifying Deployment\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    try:
        # Use CLI to verify deployment
        result = subprocess.run(
            ['act', 'workflow', 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        
        if 'getting-started-workflow' in result.stdout:
            print(f"\n\033[92m✓ Deployment verified!\033[0m")
            print(f"  Workflow: getting-started-workflow")
            print(f"  Status: Deployed and ready")
            print(f"  Region: us-east-1")
            return True
        else:
            print(f"\n\033[91m[ERROR]\033[0m Workflow not found in deployment list")
            return False
        
    except Exception as e:
        print(f"\n\033[91m[ERROR]\033[0m Could not verify deployment: {e}")
        return False


def show_invocation_example():
    """Show how to invoke the deployed workflow."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mInvoking Deployed Workflow\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    print(f"\n\033[38;5;214mCLI Invocation:\033[0m")
    print("  act workflow invoke --name getting-started-workflow")
    print("  act workflow invoke --name getting-started-workflow --payload '{\"key\": \"value\"}'")
    
    print(f"\n\033[38;5;214mPython SDK Invocation:\033[0m")
    print("""  import boto3
  
  client = boto3.client('nova-act', region_name='us-east-1')
  response = client.invoke_workflow(
      workflowDefinitionName='getting-started-workflow',
      payload={}
  )
  print(response['result'])""")
    
    print(f"\n\033[38;5;214mMonitoring:\033[0m")
    print("  • Nova Act console: https://console.aws.amazon.com/nova-act")
    print("  • CloudWatch logs for execution traces")
    print("  • S3 artifacts for workflow outputs")


def main():
    """Main execution function."""
    print("="*60)
    print("Deploying Workflows to Bedrock AgentCore")
    print("="*60)
    
    if not check_prerequisites():
        return
    
    explain_deployment()
    
    # Create deployment source
    source_dir = create_deployment_source()
    
    # Deploy workflow
    if not deploy_workflow(source_dir):
        return
    
    # Verify deployment
    if not verify_deployment():
        return
    
    # Show invocation examples
    show_invocation_example()
    
    # Cleanup
    import shutil
    shutil.rmtree(source_dir, ignore_errors=True)
    
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mDeployment Complete\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    print("1. Workflow is now running on AWS infrastructure")
    print("2. Proceed to 5_invoke_workflow.py to learn invocation")
    print("3. Monitor execution in Nova Act console")
    print("4. After invocation, proceed to 02-human-in-loop for advanced patterns")


if __name__ == "__main__":
    main()
