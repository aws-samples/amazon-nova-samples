# LangChain Text-to-Voice Migration Example

Migrates a LangChain `create_react_agent` banking assistant to a Strands BidiAgent voice agent.

## Files

| File | Role |
|------|------|
| `text_agent.py` | **BEFORE** — Original LangChain text agent with `@tool` functions and text-oriented system prompt |
| `voice_agent.py` | **AFTER** — Migrated voice session handler with voice-optimized prompt and BidiAgent |
| `voice_tools_mcp.py` | **AFTER** — Same tool logic wrapped as an MCP server for the voice agent |
| `voice_server.py` | **AFTER** — FastAPI WebSocket server that runs the voice agent |

## What Changed

1. **System prompt**: Removed JSON formatting instructions, added greeting flow, brevity rules, number spelling, transfer confirmation, and filler phrases
2. **Tools**: Same logic, wrapped as MCP server instead of LangChain `@tool` decorators
3. **Agent**: Replaced `create_react_agent` + `ChatBedrockConverse` with `BidiAgent` + `BidiNovaSonicModel`
4. **Transport**: Replaced HTTP request/response with WebSocket bidirectional audio streaming

## Run

```bash
# 1. Install dependencies
pip install uvicorn fastapi strands-agents strands-agents-tools aws_sdk_bedrock_runtime boto3

# 2. Deploy voice_tools_mcp.py behind an AgentCore MCP Gateway (get the ARN)

# 2. Start the voice server
MCP_GATEWAY_ARNS='["arn:aws:bedrock-agentcore:us-east-1:123456:gateway/gw-xxx"]' \
  python voice_server.py

# 3. Connect with the browser client
python ../../client/client.py --ws-url ws://localhost:8080/ws
```
