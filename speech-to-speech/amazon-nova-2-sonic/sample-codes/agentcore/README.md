# Amazon Nova Sonic on Bedrock AgentCore

Deploy real-time voice agents powered by Amazon Nova Sonic using Amazon Bedrock AgentCore Runtime. AgentCore handles hosting, scaling, authentication, and WebSocket proxying so you can focus on the agent logic.

## What is AgentCore?

[Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/) offers a managed bidirectional runtime for deploying AI voice agents. For Nova Sonic voice agents, it provides:

- WebSocket proxy with SigV4 authentication (pre-signed URLs)
- Container-based deployment with automatic scaling
- IAM credential management via IMDS
- MCP Gateway integration for tool access
- Health checks and lifecycle management

## Samples

This lab includes two implementations that deploy Nova Sonic voice agents to AgentCore. Both share the same deployment tooling (`deployment/`) and follow the same deploy → connect → talk workflow.

| Sample | Approach | Tools | Best For |
|--------|----------|-------|----------|
| [Strands](strands/) | Strands `BidiAgent` SDK | 4 MCP Gateways (auth, banking, mortgage, FAQ KB) | Rapid development, enterprise tool architecture |
| [Sonic](sonic/) | Native Bedrock SDK | Built-in `getDateTool` | Full protocol control, custom voice flows |

## Prerequisites

- AWS account with Bedrock and AgentCore permissions
- AWS CLI configured
- Python 3.10+
- Docker (optional, for local builds with `--local` or `--local-build` flags)

## Quick Start

### 1. Configure AWS Credentials

```bash
# Option A: Run interactive setup
aws configure
# Prompts for: AWS Access Key ID, Secret Access Key, Default region, Output format

# Option B: Export directly
export AWS_ACCESS_KEY_ID=<your-access-key>
export AWS_SECRET_ACCESS_KEY=<your-secret-key>
export AWS_DEFAULT_REGION=us-east-1

# If using temporary credentials (SSO, assumed role, etc.)
export AWS_SESSION_TOKEN=<your-session-token>
```

Verify your identity:

```bash
aws sts get-caller-identity
```

### 2. Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install deployment tooling
pip install -r deployment/requirements.txt

# Verify
agentcore --help
python deployment/deploy.py --help
```

### 3. Set Account ID

```bash
export ACCOUNT_ID=123456789012
```

### Deploy Strands (BidiAgent + MCP Gateways)

```bash
# Deploy agent runtime + 4 MCP Gateways
python deployment/deploy.py strands

# Launch the web client
./deployment/start_client.sh strands
```

The Strands sample is a banking assistant with authentication, account management, mortgage services, and FAQ powered by Bedrock Knowledge Bases. See [strands/README.md](strands/README.md) for architecture details and MCP Gateway setup.

### Deploy Sonic (Native Bedrock SDK)

```bash
# Deploy agent runtime
python deployment/deploy.py sonic

# Launch the web client
./deployment/start_client.sh sonic
```

The Sonic sample gives you direct control over the Nova Sonic bidirectional streaming protocol. See [sonic/README.md](sonic/README.md) for the event protocol reference and session lifecycle.

## How It Works

```
┌─────────────┐     Pre-signed URL     ┌──────────────────┐        ┌─────────────────┐
│   Browser   │ ◄───── WebSocket ────► │  AgentCore       │ ◄────► │  Nova Sonic     │
│   Client    │     (SigV4 auth)       │  Runtime         │        │  (Bedrock)      │
└─────────────┘                        └──────────────────┘        └─────────────────┘
                                                │
                                                │ (Strands only)
                                                ▼
                                        ┌──────────────────┐
                                        │  MCP Gateways    │
                                        │  (AgentCore)     │
                                        └──────────────────┘
```

1. `deploy.py` builds a Docker container with your agent code and pushes it to ECR
2. AgentCore creates a runtime that hosts the container and exposes a WebSocket endpoint
3. The client generates a SigV4 pre-signed URL and connects over WebSocket
4. Audio streams bidirectionally between the browser and Nova Sonic through AgentCore
5. For Strands, tool calls route through AgentCore MCP Gateways to Lambda-backed MCP servers

## Project Structure

```
agentcore/
├── deployment/              # Shared deployment tooling
│   ├── deploy.py            # Deploy strands or sonic to AgentCore
│   ├── cleanup.py           # Tear down deployed resources
│   ├── start_client.sh      # Launch the web client
│   ├── websocket_helpers.py # SigV4 pre-signed URL generation
│   ├── requirements.txt     # Deployment dependencies
│   ├── agent_role.json      # IAM role permissions
│   └── trust_policy.json    # IAM trust policy
├── strands/                 # Strands BidiAgent sample
│   ├── websocket/           # FastAPI server + agent logic
│   ├── client/              # Browser client + profiles
│   └── mcp/                 # 4 MCP servers (auth, banking, mortgage, FAQ)
├── sonic/                   # Native Bedrock SDK sample
│   ├── websocket/           # FastAPI server + session manager + events
│   └── client/              # Browser client
└── assets/                  # Architecture diagrams, FAQ data
```

## Knowledge Base Setup (Strands FAQ Tools)

The Strands sample includes FAQ tools that require a Bedrock Knowledge Base:

1. Create a Knowledge Base in the Bedrock console
2. Upload `assets/anybank-faq.md` as the data source
3. Update the AgentCore runtime environment:

```bash
AGENT_RUNTIME_ID=$(python -c "import json; print(json.load(open('strands/setup_config.json'))['agent_arn'].split('/')[-1])")

aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id $AGENT_RUNTIME_ID \
  --environment-variables KNOWLEDGE_BASE_ID=<your-kb-id> \
  --region us-east-1
```

Other Strands tools (auth, banking, mortgage) work without this step.

## Cleanup

```bash
# Remove all resources for a sample
python deployment/cleanup.py strands
python deployment/cleanup.py sonic
```

## Resources

- [AgentCore Runtime Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AgentCore Starter Toolkit](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-toolkit.html)
- [AgentCore MCP Gateway Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/mcp-gateway.html)
- [Amazon Nova Sonic Documentation](https://docs.aws.amazon.com/nova/latest/nova2-userguide/using-conversational-speech.html)
- [Strands Agents SDK](https://github.com/strands-ai/strands-agents)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Bedrock Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
