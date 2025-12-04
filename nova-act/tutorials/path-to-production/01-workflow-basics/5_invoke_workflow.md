# Invoking Deployed Workflows

## Prerequisites
```bash
pip install boto3
```

- Workflow "getting-started-workflow" deployed (from example 4)
- AWS credentials configured
- boto3 installed

## Overview
This tutorial demonstrates how to invoke workflows deployed to AgentCore using boto3. Shows how to retrieve the runtime ARN from deployment state, invoke workflows programmatically, and use results in downstream processing.

## Code Walkthrough

### Getting the AgentCore Runtime ARN
```python
def get_agentcore_runtime_arn(workflow_name, region='us-east-1'):
    """Get AgentCore runtime ARN from deployment state."""
    state_file = Path.home() / '.act_cli' / 'state' / account_id / region / 'workflows.json'
    
    with open(state_file) as f:
        state = json.load(f)
    
    workflow = state['workflows'][workflow_name]
    deployment_arn = workflow['deployments']['agentcore']['deployment_arn']
    
    return deployment_arn
```
**Explanation**: Reads the deployment state file created by the Nova Act CLI. The state file contains the AgentCore runtime ARN needed for invocation. This ARN is unique to each deployed workflow and is automatically generated during deployment.

### Basic Workflow Invocation
```python
import boto3
import json
import uuid

# Get runtime ARN from deployment state
runtime_arn = get_agentcore_runtime_arn('getting-started-workflow')

# Create AgentCore client
client = boto3.client('bedrock-agentcore', region_name='us-east-1')

# Generate session ID (must be 33+ characters)
session_id = str(uuid.uuid4()) + str(uuid.uuid4())[:5]

# Invoke workflow
response = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn,
    runtimeSessionId=session_id,
    payload=json.dumps({}),
    qualifier="DEFAULT"
)

# Read response
response_body = response['response'].read()
response_data = json.loads(response_body)
```
**Explanation**: Invokes the deployed workflow using the `bedrock-agentcore` client. The `agentRuntimeArn` is retrieved from deployment state. The `runtimeSessionId` must be at least 33 characters - we generate it using UUIDs. The `payload` is JSON-encoded and passed as a string. The response is a streaming body that must be read and decoded.

### Invocation with Payload
```python
payload_data = {
    "url": "https://nova.amazon.com/act",
    "task": "Find documentation about workflow deployment",
    "timestamp": datetime.now().isoformat()
}

response = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn,
    runtimeSessionId=session_id,
    payload=json.dumps(payload_data),
    qualifier="DEFAULT"
)
```
**Explanation**: Passes custom data to the workflow via the `payload` parameter. The payload must be JSON-encoded as a string. The workflow receives this data in its `main(payload)` function. Use this to parameterize workflow behavior - different URLs, tasks, or configuration options.

### Monitoring Workflow Execution
```python
# Extract runtime name from ARN
runtime_name = runtime_arn.split('/')[-1]
log_group = f"/aws/bedrock-agentcore/runtimes/{runtime_name}-DEFAULT"

# Access logs via boto3
logs_client = boto3.client('logs')
response = logs_client.filter_log_events(
    logGroupName=log_group,
    startTime=int((datetime.now().timestamp() - 3600) * 1000)
)

for event in response['events']:
    print(event['message'])
```
**Explanation**: CloudWatch logs are stored in a log group named after the AgentCore runtime. Extract the runtime name from the ARN and construct the log group path. Use the CloudWatch Logs API to query execution logs. The `@workflow` decorator automatically logs workflow run creation, model ID, execution timing, and errors.

### Using Results Downstream

#### Example 1: Store Results in S3
```python
response = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn,
    runtimeSessionId=session_id,
    payload=json.dumps({"task": "Extract data"}),
    qualifier="DEFAULT"
)

response_body = response['response'].read()
result = json.loads(response_body)

# Store in S3
s3_client = boto3.client('s3')
s3_client.put_object(
    Bucket='my-workflow-results',
    Key=f"results/{session_id}.json",
    Body=json.dumps(result)
)
```
**Explanation**: Workflow results can be stored in S3 for persistence. Use the `session_id` as a unique identifier for each execution. This enables audit trails and result retrieval.

#### Example 2: Publish to SNS
```python
sns_client = boto3.client('sns')
sns_client.publish(
    TopicArn='arn:aws:sns:us-east-1:123456789012:workflow-notifications',
    Subject='Workflow Completed',
    Message=json.dumps({
        'sessionId': session_id,
        'workflowName': 'getting-started-workflow',
        'result': result
    })
)
```
**Explanation**: Publish workflow results to SNS topics to trigger notifications or downstream Lambda functions. This enables event-driven architectures where workflow completion triggers other processes.

#### Example 3: Chain Workflows
```python
# First workflow
response1 = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn_1,
    runtimeSessionId=session_id_1,
    payload=json.dumps({"url": "https://example.com"}),
    qualifier="DEFAULT"
)

result1 = json.loads(response1['response'].read())

# Use first workflow's result as input to second workflow
response2 = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn_2,
    runtimeSessionId=session_id_2,
    payload=json.dumps({
        "data": result1,
        "sessionId": session_id_1
    }),
    qualifier="DEFAULT"
)
```
**Explanation**: Chain multiple workflows together by passing the output of one workflow as input to another. This enables multi-step automation where each workflow handles a specific task.

### Error Handling
```python
try:
    runtime_arn = get_agentcore_runtime_arn('getting-started-workflow')
    
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    session_id = str(uuid.uuid4()) + str(uuid.uuid4())[:5]
    
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=session_id,
        payload=json.dumps({}),
        qualifier="DEFAULT"
    )
    
except FileNotFoundError as e:
    print(f"Error: {e}")
    print("Run 4_deploy_workflow.py first")
    
except ValueError as e:
    print(f"Error: {e}")
    print("Ensure workflow is deployed to AgentCore")
    
except client.exceptions.ResourceNotFoundException:
    print("Error: AgentCore runtime not found")
    print("Redeploy the workflow")
    
except Exception as e:
    print(f"Unexpected error: {e}")
    print("Check CloudWatch logs for details")
```
**Explanation**: Handle common errors when invoking workflows:
- `FileNotFoundError`: Deployment state file not found - workflow not deployed
- `ValueError`: Workflow not deployed to AgentCore
- `ResourceNotFoundException`: AgentCore runtime doesn't exist
- General exceptions: Check CloudWatch logs for detailed error traces

## Running the Example

```bash
python 5_invoke_workflow.py
```

**Expected Output:**
```
============================================================
Invoking Deployed Workflows
============================================================

============================================================
Basic Workflow Invocation
============================================================

Workflow: getting-started-workflow
Runtime ARN: arn:aws:bedrock-agentcore:us-east-1:975050356504:runtime/getting_started_workflow-yvsFTc7fSQ

Invoking with payload: {}
Session ID: 238ca9f2-8cc8-483d-bff8-ca48b17e2368339eb

✓ Workflow invoked successfully
  Response: null

============================================================
Workflow Invocation with Payload
============================================================

Invoking with payload:
{
  "url": "https://nova.amazon.com/act",
  "task": "Find documentation about workflow deployment",
  "timestamp": "2025-11-28T16:03:09.580737"
}

✓ Workflow completed
  Session ID: 9d61106e-9272-45a5-8a56-c9740d3c14b81b621
```

## Key Concepts

**AgentCore Runtime ARN**: Unique identifier for the deployed workflow. Retrieved from the deployment state file created by the Nova Act CLI.

**bedrock-agentcore Client**: AWS SDK client for invoking AgentCore runtimes. Different from the `nova-act` client used for workflow definitions.

**Session ID**: Must be at least 33 characters. Used to track individual workflow invocations. Generate using UUIDs.

**Payload Encoding**: Must be JSON-encoded as a string. The workflow receives the decoded payload in its `main(payload)` function.

**Response Streaming**: The response body is a streaming object that must be read and decoded to get the result.

**Deployment State**: The Nova Act CLI stores deployment information in `~/.act_cli/state/`. This includes the AgentCore runtime ARN needed for invocation.

## Troubleshooting

**Deployment state not found**: Run `4_deploy_workflow.py` to deploy the workflow first

**Runtime ARN not found**: Ensure the workflow was deployed to AgentCore (not just created as a definition)

**Session ID too short**: Must be at least 33 characters - use UUID generation as shown

**Payload encoding error**: Ensure payload is JSON-encoded with `json.dumps()`

**Response read error**: The response body is a streaming object - must call `.read()` before decoding

## Congratulations!

You've completed the workflow basics for Nova Act on AWS! 

**What You've Learned:**
- ✓ Create workflow definitions in AWS
- ✓ Use the `@workflow` decorator for AWS execution  
- ✓ Manage multiple browser sessions with context managers
- ✓ Deploy workflows to Bedrock AgentCore
- ✓ Invoke deployed workflows via boto3
- ✓ Use workflow results in downstream processing
- ✓ Monitor workflow execution via CloudWatch

You're now ready to build production Nova Act workflows on AWS!
