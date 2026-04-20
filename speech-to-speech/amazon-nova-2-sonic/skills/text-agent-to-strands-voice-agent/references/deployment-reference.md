# Deployment to AgentCore Reference

Detailed reference for deploying the voice agent to Amazon Bedrock AgentCore Runtime. For the overview, see SKILL.md Part 3.

## Deployment Script Workflow

The `deployment/deploy.py` script runs these steps in order:

### 1. Prerequisites Check

Verifies `python3`, `aws` CLI, and `agentcore` (bedrock-agentcore-starter-toolkit) are installed.

```bash
pip install bedrock-agentcore-starter-toolkit
```

### 2. MCP Gateway Deployment

For each tool group, the script:
1. Creates an MCP Gateway via `GatewayClient.create_mcp_gateway()`
2. Creates a Lambda-backed MCP Server Target via `create_mcp_gateway_target()`
3. Stores the gateway ARN and URL

The default tool groups for the banking demo:

| Gateway | MCP Server | Tools |
|---------|-----------|-------|
| auth-tools | auth-tools-mcp | `authenticate_user`, `verify_identity` |
| banking-tools | banking-tools-mcp | `get_account_balance`, `get_recent_transactions`, `transfer_funds`, `get_account_summary` |
| mortgage-tools | mortgage-tools-mcp | `get_mortgage_rates`, `calculate_mortgage_payment`, `check_mortgage_eligibility`, `get_mortgage_application_status` |
| faq-kb-tools | anybank-faq-kb | `search_anybank_faq`, `answer_anybank_question` |

To deploy your own tools, modify the `gateway_configs` list in `deploy.py` or create gateways manually via the AWS console / CLI.

### 3. AgentCore Memory (Optional)

Creates a memory resource for conversation persistence:

```python
from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name="us-east-1")
memory = client.create_memory(
    name="my-voice-agent_memory",
    description="Chat history for my-voice-agent",
)
# memory["id"] → set as MEMORY_ID env var
```

The agent loads the last K conversation turns into the system prompt at session start, and saves each user/assistant message during the session.

### 4. Observability (Optional)

Creates a CloudWatch observability destination:

```python
client = boto3.client('bedrock-agentcore-control', region_name="us-east-1")
response = client.create_observability_configuration(
    name="my-voice-agent_observability",
    destinationType="CLOUDWATCH",
)
# response["otlpEndpoint"] → set as OTEL_EXPORTER_OTLP_TRACES_ENDPOINT env var
```

The agent initializes OpenTelemetry tracing at startup if the endpoint is set.

### 5. IAM Role

Creates `WebSocketStrandsAgentRole` with these permissions:
- `bedrock:InvokeModel` — for Nova Sonic
- `bedrock-agentcore:InvokeGateway` — for MCP Gateway tool calls
- `ecr:*` — for pushing the container image
- `logs:*` — for CloudWatch logging

Policy templates are in `deployment/agent_role.json` and `deployment/trust_policy.json`.

### 6. ECR + Runtime Launch

Uses `bedrock-agentcore-starter-toolkit` to:
1. Build the Docker image from `strands/websocket/Dockerfile`
2. Create an ECR repository (if `ecr_auto_create: true`)
3. Push the image
4. Create or update the AgentCore Runtime
5. Pass environment variables (`MCP_GATEWAY_ARNS`, `MEMORY_ID`, etc.)

Two build modes:
- **CodeBuild** (default) — no local Docker required, builds in AWS
- **Local build** (`--local-build`) — requires Docker installed locally

### Environment Variables Passed to Runtime

| Variable | Value | Purpose |
|----------|-------|---------|
| `MCP_GATEWAY_ARNS` | `["arn:...","arn:..."]` | JSON array of MCP Gateway ARNs for tool access |
| `MCP_GATEWAY_URLS` | `["https://...","https://..."]` | JSON array of gateway URLs (for logging) |
| `MEMORY_ID` | `mem-xxxxx` | AgentCore Memory ID for conversation persistence |
| `MEMORY_REGION` | `us-east-1` | Region for the memory client |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | `https://...` | OTLP endpoint for OpenTelemetry traces |
| `OTEL_SERVICE_NAME` | `my-voice-agent` | Service name for traces |

## Connecting After Deployment

### Browser Client with Presigned URL

```bash
python strands/client/client.py \
    --runtime-arn arn:aws:bedrock-agentcore:us-east-1:123456:runtime/RTID \
    --region us-east-1 \
    --expires 3600
```

This:
1. Generates a SigV4 presigned WebSocket URL (valid for `--expires` seconds)
2. Starts an HTTP server on `localhost:8000`
3. Serves the HTML client with the URL pre-populated
4. Opens the browser

### Using start_client.sh

After deployment, the config is saved to `strands/setup_config.json`. The helper script reads it:

```bash
./deployment/start_client.sh strands
```

## Cleanup

```bash
python deployment/cleanup.py strands
```

This removes:
- AgentCore Runtime
- ECR repository and images
- MCP Gateways and targets
- IAM role and policies
- Memory resource
- Observability destination
- Local config files

## Manual Deployment (Without deploy.py)

If you prefer to deploy manually:

1. Create IAM role with `deployment/agent_role.json` policy
2. Create MCP Gateways via AWS console or CLI
3. Build and push Docker image to ECR
4. Create `.bedrock_agentcore.yaml` (see SKILL.md Part 3)
5. Run `agentcore launch` or use the starter toolkit API
6. Set environment variables on the Runtime
