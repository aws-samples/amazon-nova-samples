#!/usr/bin/env python3
"""
Invoking Deployed Workflows with Boto3

This script demonstrates how to invoke deployed workflows using the AWS SDK (boto3).
Shows how to pass payloads, retrieve results, and use workflow outputs downstream.

Prerequisites:
- Completed 4_deploy_workflow.py
- Workflow "getting-started-workflow" deployed to AgentCore
- AWS credentials configured
- boto3 installed: pip install boto3

Setup:
1. Ensure workflow is deployed (run 4_deploy_workflow.py)
2. Run this script to invoke the workflow
3. Observe how results are returned and can be used

Note: Workflows execute asynchronously on AWS infrastructure via AgentCore.
"""

import boto3
import json
import os
import uuid
from datetime import datetime
from pathlib import Path


def get_agentcore_runtime_arn(workflow_name, region='us-east-1'):
    """Get AgentCore runtime ARN from deployment state."""
    # Read deployment state from CLI state file
    state_file = Path.home() / '.act_cli' / 'state' / boto3.client('sts').get_caller_identity()['Account'] / region / 'workflows.json'
    
    if not state_file.exists():
        raise FileNotFoundError(f"Deployment state not found: {state_file}")
    
    with open(state_file) as f:
        state = json.load(f)
    
    workflow = state.get('workflows', {}).get(workflow_name)
    if not workflow:
        raise ValueError(f"Workflow '{workflow_name}' not found in deployment state")
    
    deployment_arn = workflow.get('deployments', {}).get('agentcore', {}).get('deployment_arn')
    if not deployment_arn:
        raise ValueError(f"Workflow '{workflow_name}' not deployed to AgentCore")
    
    return deployment_arn


def invoke_workflow_basic():
    """Basic workflow invocation with empty payload."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mBasic Workflow Invocation\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    # Get AgentCore runtime ARN from deployment state
    workflow_name = 'getting-started-workflow'
    runtime_arn = get_agentcore_runtime_arn(workflow_name)
    
    print(f"\nWorkflow: {workflow_name}")
    print(f"Runtime ARN: {runtime_arn}")
    
    # Create AgentCore client
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Generate session ID (must be 33+ characters)
    session_id = str(uuid.uuid4()) + str(uuid.uuid4())[:5]
    
    # Invoke workflow
    print(f"\nInvoking with payload: {{}}")
    print(f"Session ID: {session_id}")
    
    payload = json.dumps({})
    
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=session_id,
        payload=payload,
        qualifier="DEFAULT"
    )
    
    # Read response
    response_body = response['response'].read()
    response_data = json.loads(response_body)
    
    print(f"\n\033[92m✓ Workflow invoked successfully\033[0m")
    print(f"  Response: {json.dumps(response_data, indent=2)}")
    
    return response_data


def invoke_workflow_with_payload():
    """Invoke workflow with custom payload data."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mWorkflow Invocation with Payload\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    workflow_name = 'getting-started-workflow'
    runtime_arn = get_agentcore_runtime_arn(workflow_name)
    
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    session_id = str(uuid.uuid4()) + str(uuid.uuid4())[:5]
    
    # Custom payload with parameters
    payload_data = {
        "url": "https://nova.amazon.com/act",
        "task": "Find documentation about workflow deployment",
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"\nInvoking with payload:")
    print(json.dumps(payload_data, indent=2))
    
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=session_id,
        payload=json.dumps(payload_data),
        qualifier="DEFAULT"
    )
    
    response_body = response['response'].read()
    response_data = json.loads(response_body)
    
    print(f"\n\033[92m✓ Workflow completed\033[0m")
    print(f"  Session ID: {session_id}")
    
    return response_data


def use_workflow_results_downstream():
    """Demonstrate using workflow results in downstream processing."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mUsing Workflow Results Downstream\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    workflow_name = 'getting-started-workflow'
    runtime_arn = get_agentcore_runtime_arn(workflow_name)
    
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    session_id = str(uuid.uuid4()) + str(uuid.uuid4())[:5]
    
    # Invoke workflow
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=session_id,
        payload=json.dumps({"task": "Extract key information"}),
        qualifier="DEFAULT"
    )
    
    response_body = response['response'].read()
    result = json.loads(response_body)
    
    # Example 1: Store results in S3
    print("\n1. Storing results in S3:")
    bucket_name = 'my-workflow-results'
    key = f"results/{session_id}.json"
    
    print(f"   Bucket: {bucket_name}")
    print(f"   Key: {key}")
    print(f"   (Skipping actual S3 upload in demo)")
    
    # Example 2: Send results to SNS
    print("\n2. Publishing results to SNS:")
    print(f"   Topic: arn:aws:sns:us-east-1:123456789012:workflow-notifications")
    print(f"   Message: Workflow {session_id} completed")
    print(f"   (Skipping actual SNS publish in demo)")
    
    # Example 3: Store in DynamoDB
    print("\n3. Storing metadata in DynamoDB:")
    print(f"   Table: workflow-executions")
    print(f"   Item: {{")
    print(f"     'sessionId': '{session_id}',")
    print(f"     'workflowName': '{workflow_name}',")
    print(f"     'timestamp': '{datetime.now().isoformat()}'")
    print(f"   }}")
    print(f"   (Skipping actual DynamoDB put in demo)")
    
    # Example 4: Trigger another workflow
    print("\n4. Chaining workflows:")
    print(f"   Next workflow: data-processing-workflow")
    print(f"   Input: Results from {workflow_name}")
    print(f"   (Skipping actual workflow chain in demo)")
    
    return result


def monitor_workflow_logs():
    """Show how to access CloudWatch logs for workflow execution."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mMonitoring Workflow Execution\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    workflow_name = 'getting-started-workflow'
    runtime_arn = get_agentcore_runtime_arn(workflow_name)
    
    # Extract runtime name from ARN
    runtime_name = runtime_arn.split('/')[-1]
    log_group = f"/aws/bedrock-agentcore/runtimes/{runtime_name}-DEFAULT"
    
    print(f"\nCloudWatch Log Group:")
    print(f"  {log_group}")
    
    print(f"\nAccess logs via AWS CLI:")
    print(f"  aws logs tail {log_group} --follow")
    print(f"  aws logs tail {log_group} --since 1h")
    
    print(f"\nAccess logs via boto3:")
    print(f"""
    logs_client = boto3.client('logs')
    response = logs_client.filter_log_events(
        logGroupName='{log_group}',
        startTime=int((datetime.now().timestamp() - 3600) * 1000)
    )
    for event in response['events']:
        print(event['message'])
    """)
    
    print(f"\nWorkflow Definition Logging:")
    print(f"  The @workflow decorator automatically logs:")
    print(f"  • Workflow run creation")
    print(f"  • Model ID being used")
    print(f"  • Execution start/completion")
    print(f"  • Any errors or exceptions")


def error_handling_example():
    """Demonstrate error handling for workflow invocations."""
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mError Handling\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    try:
        workflow_name = 'getting-started-workflow'
        runtime_arn = get_agentcore_runtime_arn(workflow_name)
        
        client = boto3.client('bedrock-agentcore', region_name='us-east-1')
        session_id = str(uuid.uuid4()) + str(uuid.uuid4())[:5]
        
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=session_id,
            payload=json.dumps({}),
            qualifier="DEFAULT"
        )
        
        print(f"\n\033[92m✓ Workflow invoked successfully\033[0m")
        print(f"  Session ID: {session_id}")
            
    except FileNotFoundError as e:
        print(f"\n\033[91m✗ Error: {e}\033[0m")
        print("  Run 4_deploy_workflow.py first")
        
    except ValueError as e:
        print(f"\n\033[91m✗ Error: {e}\033[0m")
        print("  Ensure workflow is deployed to AgentCore")
        
    except client.exceptions.ResourceNotFoundException:
        print("\n\033[91m✗ Error: AgentCore runtime not found\033[0m")
        print("  Redeploy the workflow")
        
    except Exception as e:
        print(f"\n\033[91m✗ Unexpected error: {e}\033[0m")
        print("  Check CloudWatch logs for details")


def main():
    """Run all workflow invocation examples."""
    print(f"\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mInvoking Deployed Workflows\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    
    # Example 1: Basic invocation
    invoke_workflow_basic()
    
    # Example 2: Invocation with payload
    import time
    time.sleep(2)
    invoke_workflow_with_payload()
    
    # Example 3: Using results downstream
    time.sleep(2)
    use_workflow_results_downstream()
    
    # Example 4: Monitoring
    monitor_workflow_logs()
    
    # Example 5: Error handling
    error_handling_example()
    
    print(f"\n\033[38;5;214m{'='*60}\033[0m")
    print(f"\033[38;5;214mCongratulations!\033[0m")
    print(f"\033[38;5;214m{'='*60}\033[0m")
    print("\n\033[92mYou've completed the workflow basics!\033[0m\n")
    print("You now know how to:")
    print("  ✓ Create workflow definitions in AWS")
    print("  ✓ Use the @workflow decorator for AWS execution")
    print("  ✓ Manage multiple browser sessions with context managers")
    print("  ✓ Deploy workflows to Bedrock AgentCore")
    print("  ✓ Invoke deployed workflows via boto3")
    print("  ✓ Use workflow results in downstream processing")
    print("  ✓ Monitor workflow execution via CloudWatch")
    print("\nYou're ready to build production Nova Act workflows on AWS!")


if __name__ == "__main__":
    main()
