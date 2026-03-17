# AgentCore Gateway Integration Tutorial

## Overview

This tutorial demonstrates how to integrate Amazon Bedrock AgentCore Gateway with Nova Act for enterprise infrastructure planning. You'll learn how to create a unified MCP endpoint that combines multiple tool types (Lambda functions) and use them with browser automation for real-world capacity planning scenarios.

## Use Case: GPU Capacity Planning for LLM Training

**Scenario**: You're planning to train a large language model and need to determine how many AWS P5.48xlarge instances are required based on the model size.

**Workflow**:
1. User specifies model size (e.g., 120B parameters)
2. Nova Act scrapes NVIDIA H100 GPU specifications from the web
3. Gateway calculator tools compute memory requirements (parameters × 2 bytes for FP16)
4. Gateway calculator tools compute total memory per instance (8 GPUs × 80GB)
5. Gateway calculator tools calculate instances needed (model memory ÷ instance memory)
6. Display clean summary with final instance count

**Why AgentCore Gateway?**
- **Unified Endpoint**: Single MCP URL for multiple tool types (Lambda, MCP servers, APIs)
- **Centralized Management**: Register, update, and synchronize tools in one place
- **Enterprise Ready**: IAM-based authentication, logging, and access control
- **Tool Discovery**: Automatic tool catalog with semantic search capabilities

## What You'll Build

1. **Calculator Lambda Function**: Provides `multiply_numbers` and `divide_numbers` tools
2. **AgentCore Gateway**: Unified MCP endpoint hosting the Lambda tools
3. **Nova Act Workflow**: Combines Gateway tools with browser automation for capacity planning

## Prerequisites

- Nova Act installed: `pip install nova-act`
- boto3 installed: `pip install boto3`
- AWS credentials configured with permissions for:
  - Lambda (create/invoke functions)
  - IAM (create roles and policies)
  - AgentCore Gateway (create gateways and targets)
- Understanding of AgentCore Gateway concepts (see [AWS Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html))

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Nova Act Workflow                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Browser Automation (Nvidia H100 specs)              │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Gateway Tools (multiply, divide)                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              AgentCore Gateway (MCP Endpoint)               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Target: Calculator Lambda                           │  │
│  │    - multiply_numbers(number1, number2)              │  │
│  │    - divide_numbers(number1, number2)                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              AWS Lambda Function                            │
│              gateway-calculator-tools                       │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Guide

### Step 1: Create Workflow Definition

The script uses the `@workflow` decorator to enable AWS logging:

```python
@workflow(workflow_definition_name="gateway-integration-demo", model_id="nova-act-latest")
def demonstrate_gateway_workflow(gateway_id, model_size_b):
    # Workflow implementation
```

**What happens:**
- Creates workflow definition in Nova Act Service
- Enables CloudWatch Logs for execution tracking
- Provides ARN for monitoring and debugging

**User interaction:**
```
Create workflow definition? (yes/no): yes
```

### Step 2: Deploy Calculator Lambda

The script deploys a Lambda function with two mathematical tools:

**Tools:**
- `multiply_numbers(number1, number2)` → Returns product
- `divide_numbers(number1, number2)` → Returns quotient

**IAM Role:**
- Trust policy: `lambda.amazonaws.com`
- Permissions: Basic Lambda execution

**User interaction:**
```
Deploy Lambda function? (yes/no): yes
```

### Step 3: Create AgentCore Gateway

The Gateway provides a unified MCP endpoint for all tools.

**Components:**
1. **Gateway IAM Role**
   - Trust: `bedrock-agentcore.amazonaws.com`
   - Permissions: Gateway operations, Lambda invoke, Secrets Manager

2. **Gateway Configuration**
   - Protocol: MCP
   - Authorization: NONE (for demo purposes)
   - Status: READY (after creation)

**User interaction:**
```
Create AgentCore Gateway? (yes/no): yes
Create IAM role for Gateway? (yes/no): yes
```

### Step 4: Register Lambda Target

Registers the calculator Lambda as a Gateway target.

**Target Configuration:**
```python
{
    'mcp': {
        'lambda': {
            'lambdaArn': 'arn:aws:lambda:region:account:function:gateway-calculator-tools',
            'toolSchema': {
                'inlinePayload': [
                    {
                        'name': 'multiply_numbers',
                        'description': 'Multiplies two numbers',
                        'inputSchema': {
                            'type': 'object',
                            'properties': {
                                'number1': {'type': 'number'},
                                'number2': {'type': 'number'}
                            }
                        }
                    },
                    # ... divide_numbers schema
                ]
            }
        }
    }
}
```

**Credential Provider:** `GATEWAY_IAM_ROLE` (uses Gateway's IAM role to invoke Lambda)

**User interaction:**
```
Register Lambda target? (yes/no): yes
```

### Step 5: Execute Workflow

The workflow combines browser automation with Gateway tools:

**User Input:**
```
Enter model size for capacity planning:
  Model parameters (in billions, e.g., 120): 120

Execute workflow? (yes/no): yes
```

**Workflow Steps:**
1. Navigate to NVIDIA H100 page
2. Extract GPU memory (80GB)
3. Calculate model memory: 120B × 2 bytes = 240GB
4. Calculate instance memory: 8 GPUs × 80GB = 640GB
5. Calculate instances: 240GB ÷ 640GB = 0.375 → 1 instance

**Output:**
```
✓ Workflow Completed

────────────────────────────────────────────────────────────
GPU Capacity Planning Summary
────────────────────────────────────────────────────────────

  Model: 120B parameters
  Memory Required: 240GB (FP16 precision)
  Instance Type: P5.48xlarge (8× H100 80GB GPUs)
  Total Memory per Instance: 640GB

  → Instances Required: 1

  Calculation: 240GB ÷ 640GB = 0.3750 → 1 instance(s)
```

## Key Concepts

### AgentCore Gateway

**What is it?**
A managed service that provides a unified MCP endpoint for multiple tool types:
- Lambda functions
- MCP servers (remote)
- OpenAPI/Smithy APIs

**Benefits:**
- Single URL for all tools
- Automatic tool discovery and synchronization
- IAM-based access control
- Semantic search across tools
- Centralized logging and monitoring

### Gateway Targets

**Target Types:**
1. **Lambda**: AWS Lambda functions with tool schemas
2. **MCP Server**: Remote MCP servers (requires OAuth)
3. **API**: OpenAPI or Smithy model endpoints

**Credential Providers:**
- `GATEWAY_IAM_ROLE`: Uses Gateway's IAM role
- `OAUTH`: OAuth2 authentication
- `API_KEY`: API key authentication

### Tool Schema

Defines the tool interface for the Gateway:

```json
{
  "name": "multiply_numbers",
  "description": "Multiplies two numbers",
  "inputSchema": {
    "type": "object",
    "properties": {
      "number1": {"type": "number"},
      "number2": {"type": "number"}
    },
    "required": ["number1", "number2"]
  }
}
```

## Running the Tutorial

```bash
cd tutorials/path-to-production/03-tool-use
python 2_agentcore_gateway.py
```

**Interactive Prompts:**
1. Create workflow definition? → `yes`
2. Deploy Lambda function? → `yes` (or use existing)
3. Create Gateway? → `yes` (or use existing)
4. Create IAM role? → `yes` (if needed)
5. Register Lambda target? → `yes`
6. Enter model size → e.g., `120`
7. Execute workflow? → `yes`

## Troubleshooting

### No tools available from Gateway

**Cause:** Lambda target not registered

**Solution:**
- Check Gateway targets: `aws bedrock-agentcore-control list-gateway-targets --gateway-identifier <id>`
- Re-run script and answer "yes" to register Lambda target

### Lambda invocation failed

**Cause:** Gateway IAM role lacks Lambda invoke permissions

**Solution:**
- Check role policy includes `lambda:InvokeFunction`
- Verify Lambda resource policy allows Gateway role

### Gateway creation conflict

**Cause:** Gateway with same name already exists

**Solution:**
- Script will detect and offer to use existing Gateway
- Answer "yes" to use existing, "no" to skip

## Cost Considerations

**Resources Created:**
- Lambda function: Free tier eligible (1M requests/month)
- AgentCore Gateway: Pay per request
- Nova Act workflow: Pay per execution

**Estimated Cost (for tutorial):**
- Lambda: ~$0.00 (within free tier)
- Gateway: ~$0.01 per workflow execution
- Total: < $0.10 for multiple test runs

## Cleanup

To remove resources created by this tutorial:

```bash
# Delete Gateway targets
aws bedrock-agentcore-control delete-gateway-target \
  --gateway-identifier <gateway-id> \
  --target-id <target-id>

# Delete Gateway
aws bedrock-agentcore-control delete-gateway \
  --gateway-identifier <gateway-id>

# Delete Lambda function
aws lambda delete-function \
  --function-name gateway-calculator-tools

# Delete IAM roles
aws iam delete-role-policy \
  --role-name gateway-calculator-lambda-role \
  --policy-name LambdaBasicExecution

aws iam delete-role \
  --role-name gateway-calculator-lambda-role

aws iam delete-role-policy \
  --role-name agentcore-enterprise-tool-gateway-role \
  --policy-name AgentCoreGatewayPolicy

aws iam delete-role \
  --role-name agentcore-enterprise-tool-gateway-role
```

## Next Steps

1. **Add More Tools**: Register additional Lambda functions or MCP servers
2. **Implement OAuth**: Configure OAuth for MCP server targets (e.g., AWS Knowledge MCP)
3. **Custom Workflows**: Build domain-specific workflows combining Gateway tools
4. **Production Deployment**: Add error handling, retries, and monitoring
5. **Multi-Region**: Deploy Gateway in multiple regions for global access

## Additional Resources

- [AgentCore Gateway Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Nova Act Documentation](https://nova-act.readthedocs.io/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

## Related Tutorials

- `1_mcp_integration.py`: Direct MCP integration with AWS Knowledge server
- `3_production_deployment.py`: Production-ready deployment patterns (coming soon)
