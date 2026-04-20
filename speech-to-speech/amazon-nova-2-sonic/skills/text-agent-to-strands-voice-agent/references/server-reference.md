# Server Implementation Reference

Detailed reference for the FastAPI WebSocket voice agent server. For the minimal version, see SKILL.md Step 2. This covers production concerns.

## Full Session Handler

The production session handler in `strands/websocket/agent.py` includes:

- **Config event parsing**: Waits for the first WebSocket message with voice, model, region, sample rates, system prompt, and gateway ARNs
- **Multi-model support**: Creates `BidiNovaSonicModel`, `BidiOpenAIRealtimeModel`, or `BidiGeminiLiveModel` based on `model_id`
- **Text input routing**: Handles `text_input` messages alongside audio frames
- **Memory integration**: Optional AgentCore Memory for conversation persistence across sessions
- **Observability**: Optional OpenTelemetry tracing via `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`

### Config Event Schema

```json
{
    "type": "config",
    "voice": "matthew",
    "model_id": "amazon.nova-2-sonic-v1:0",
    "region": "us-east-1",
    "input_sample_rate": 16000,
    "output_sample_rate": 16000,
    "system_prompt": "...",
    "gateway_arns": ["arn:aws:bedrock-agentcore:..."],
    "api_key": null,
    "session_id": "session_20240304",
    "actor_id": "user"
}
```

Fields:
- `voice`: TTS voice — `tiffany`, `matthew`, `ruth`, `gregory`, `joanna` (Nova Sonic)
- `model_id`: Model identifier prefix determines which BidiModel class to use
- `region`: AWS region for Nova Sonic
- `input_sample_rate` / `output_sample_rate`: Must match the model (16kHz Nova, 24kHz OpenAI/Gemini)
- `system_prompt`: The voice-optimized prompt migrated from the text agent
- `gateway_arns`: MCP Gateway ARNs for tool access
- `api_key`: Required for OpenAI and Gemini models, ignored for Nova Sonic
- `session_id` / `actor_id`: For AgentCore Memory persistence (optional)

### Large Event Splitting

WebSocket frames have size limits. The server splits large audio events into chunks aligned to base64 boundaries:

```python
MAX_WS_MESSAGE_SIZE = 10000

def split_large_event(event_dict, max_size=MAX_WS_MESSAGE_SIZE):
    event_json = json.dumps(event_dict)
    if len(event_json.encode("utf-8")) <= max_size:
        return [event_dict]

    if "audio" not in event_dict:
        return [event_dict]

    audio = event_dict["audio"]
    template = {k: v for k, v in event_dict.items() if k != "audio"}
    overhead = len(json.dumps({**template, "audio": ""}).encode("utf-8"))
    chunk_size = ((max_size - overhead - 100) // 4) * 4  # base64 alignment

    chunks = []
    for i in range(0, len(audio), chunk_size):
        chunk = {**template, "audio": audio[i:i + chunk_size]}
        chunks.append(chunk)
    return chunks
```

### Credential Refresh (EC2 Deployment)

When deployed on EC2 via AgentCore Runtime, the server refreshes IAM credentials from IMDS automatically. See `strands/websocket/server.py` for the full implementation including IMDSv2 token handling and background refresh task.

### Requirements

System prerequisite (macOS):
```bash
brew install portaudio
```

System prerequisite (Debian/Ubuntu):
```bash
apt-get install -y portaudio19-dev gcc g++ make
```

Python packages:
```
uvicorn[standard]==0.34.2
fastapi==0.123.9
websockets>=14.0
strands-agents==1.25.0
strands-agents-tools==0.2.20
aws_sdk_bedrock_runtime==0.3.0
pyaudio==0.2.14
requests==2.32.5
boto3>=1.34.0
botocore>=1.34.0
```

`aws_sdk_bedrock_runtime` and `pyaudio` are not installed automatically by `strands-agents` — both must be listed explicitly:
- `aws_sdk_bedrock_runtime` — CRT-based bidirectional streaming client used by `BidiNovaSonicModel`
- `pyaudio` — imported at module level by `strands.experimental.bidi.io.audio` (requires `portaudio` system library)

Optional extras:
```
pip install 'strands-agents[bidi-openai]'   # OpenAI Realtime
pip install 'strands-agents[bidi-gemini]'   # Gemini Live
```

## Tool Migration Pattern

To migrate text agent tools to MCP servers for voice:

1. **Extract** the tool's name, description, and input schema from the text agent
2. **Create** an MCP server with matching `Tool` definitions
3. **Implement** `call_tool` to invoke the existing function logic
4. **Deploy** behind an AgentCore MCP Gateway
5. **Pass** the gateway ARN to `mcp_gateway_arn` on the BidiModel

The tool function itself doesn't change — only the wrapper. See `strands/mcp/banking_mcp.py` and `strands/mcp/auth_mcp.py` for complete examples.
