---
name: text-agent-to-nova-sonic-voice
description: "Migrate any text-based agent to a Nova Sonic voice agent using Strands BidiAgent. Covers two layers: (1) Frontend — browser WebSocket client with Web Audio API for mic capture and audio playback, (2) Orchestrator — FastAPI + Strands BidiAgent server that takes the text agent's system prompt and tools and runs them as a real-time speech-to-speech agent. TRIGGER when: user wants to add voice to an existing text agent; user asks about converting a chatbot to a Nova Sonic voice agent; user mentions text-to-voice migration, Strands BidiAgent, or Nova Sonic voice agent. SKIP when: user is building a text-only agent; user wants TTS/STT without a live agent loop; user is asking about deployment or infrastructure."
---

# Migrate a Text Agent to a Nova Sonic Voice Agent

This skill converts any text-based agent into a real-time voice agent using Strands BidiAgent with Amazon Nova Sonic. The migration is broken into two layers:

1. **Frontend** — Browser client that captures mic audio and plays back voice responses over WebSocket
2. **Orchestrator** — FastAPI + BidiAgent server that takes the text agent's system prompt and tools and runs them as a bidirectional audio streaming agent

```
┌──────────────┐    ┌──────────────────────────────────────────┐
│   Frontend   │    │            Orchestrator                  │
│              │    │                                          │
│  Browser Mic  ─────▶ FastAPI /ws ──▶ BidiAgent ──▶ Nova Sonic│
│              │    │                     │                    │
│  Speaker ◀────────── WebSocket ◀── BidiAgent ◀── Nova Sonic  │
│              │    │                     │                    │
└──────────────┘    │              Tools (Strands @tool)       │
                    └──────────────────────────────────────────┘
```

## Prerequisites — Extract from the Text Agent

Before starting, locate these in the existing text agent (any framework):

| What | What to look for |
|------|-----------------|
| System prompt | The persona/instructions string passed to the LLM |
| Tools / functions | Name, description, and input schema of each callable tool |
| Model config | Temperature, max tokens, provider-specific settings |

The extraction is framework-agnostic. Look for the system message and tool definitions in whatever orchestrator you're using — LangChain, CrewAI, AutoGen, raw OpenAI, Strands, Bedrock Converse, or custom code.

---

## Part 1 — Frontend

The frontend is a browser-based WebSocket client that captures microphone audio, streams it to the orchestrator, and plays back audio responses. It also supports text input as a fallback.

### WebSocket Connection and Config Event

On connect, the client sends a config event with the voice-optimized system prompt:

```javascript
const ws = new WebSocket("ws://localhost:8080/ws");
ws.onopen = () => {
    ws.send(JSON.stringify({
        type: "config",
        voice: "matthew",                   // Nova Sonic voice
        model_id: "amazon.nova-2-sonic-v1:0",
        region: "us-east-1",
        input_sample_rate: 16000,           // Nova Sonic requires 16kHz
        output_sample_rate: 16000,
        system_prompt: voiceOptimizedPrompt  // migrated from text agent
    }));
};
```

### Microphone Capture (AudioWorklet → base64 PCM)

```javascript
const audioCtx = new AudioContext({ sampleRate: 16000 });
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
const source = audioCtx.createMediaStreamSource(stream);

await audioCtx.audioWorklet.addModule(processorUrl);
const worklet = new AudioWorkletNode(audioCtx, "pcm-processor");
source.connect(worklet);

worklet.port.onmessage = (e) => {
    ws.send(JSON.stringify({ type: "bidi_audio_input", audio: toBase64(e.data), format: "pcm", sample_rate: 16000, channels: 1 }));
};
```

The AudioWorklet converts float32 samples to int16 PCM. The main thread base64-encodes and sends over WebSocket.

### Audio Playback and Event Handling

```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    switch (data.type) {
        case "bidi_audio_stream":  playAudioChunk(data.audio); break;   // base64 → PCM → speaker
        case "bidi_transcript_stream": displayTranscript(data.role, data.text); break;
        case "tool_use_stream":    showToolCall(data.current_tool_use.name); break;
        case "system":             showSystemMessage(data.message); break;
    }
};
```

### Text Input Fallback

```javascript
function sendText(text) {
    ws.send(JSON.stringify({ type: "text_input", text }));
}
```

### Client Options

| Client | Location | Usage |
|--------|----------|-------|
| Browser (recommended) | `strands/client/strands-client.html` | Full UI with config modal, transcript, event log |
| Python CLI | `strands/client/client.py` | Terminal client with `pyaudio` for mic/speaker |

For the browser client, a Python HTTP server (`client.py`) serves the HTML:

```bash
python strands/client/client.py --ws-url ws://localhost:8080/ws
```

For detailed audio capture/playback implementation, see [references/client-reference.md](references/client-reference.md).

---

## Part 2 — Orchestrator

The orchestrator is a FastAPI WebSocket server that wraps Strands `BidiAgent` with `BidiNovaSonicModel`. It receives the config event from the frontend, creates the agent with the voice-optimized prompt and tools, and runs the bidirectional audio loop.

### Voice-Optimize the System Prompt

The text agent's system prompt must be rewritten for voice. Key transformations:

| Text pattern | Voice replacement |
|-------------|-------------------|
| "Respond with JSON / markdown / tables" | "Speak naturally. Never mention formatting." |
| "Provide comprehensive, detailed responses" | "Keep each response to one or two sentences." |
| `$15,234.56` | "fifteen thousand two hundred thirty-four dollars and fifty-six cents" |
| "Return error code and description" | "Apologize briefly and suggest what to try next" |
| (no greeting) | "Start with: Hello! Welcome to [Service]. May I have your name?" |
| (no confirmation) | "Before any action, repeat the details back and wait for confirmation" |

Add these to every voice prompt:

```
Use brief acknowledgments: "Sure thing!", "Let me check that for you."
If you don't understand: "I'm sorry, could you say that again?"
After helping: "Is there anything else I can help with?"
End warmly: "Thanks for calling, [name]. Have a great day!"
```

For a complete before/after example, see [references/voice-prompt-guide.md](references/voice-prompt-guide.md).

### Server (server.py)

The WebSocket server defaults to port 8080. Override via `--port` flag or `PORT` environment variable:

```bash
# Default (port 8080)
python server.py

# Custom port
python server.py --port 9000

# Or via environment variable
PORT=9000 python server.py
```

```python
import logging, os, json, uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from agent import handle_websocket_session

app = FastAPI(title="Voice Agent Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    await handle_websocket_session(websocket)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8080")))
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
```

The client must connect to the same port: `ws://localhost:8080/ws` (or whichever port you chose).

### Dependencies

System prerequisite (macOS):
```bash
brew install portaudio
```

System prerequisite (Debian/Ubuntu):
```bash
apt-get install -y portaudio19-dev gcc g++ make
```

Python packages:
```bash
pip install uvicorn fastapi websockets strands-agents strands-agents-tools aws_sdk_bedrock_runtime pyaudio boto3
```

`aws_sdk_bedrock_runtime` and `pyaudio` are not installed automatically by `strands-agents` — both must be installed explicitly:
- `aws_sdk_bedrock_runtime` — CRT-based bidirectional streaming client used by `BidiNovaSonicModel`
- `pyaudio` — imported at module level by `strands.experimental.bidi.io.audio` (requires `portaudio` system library)

### Session Handler (agent.py)

```python
from fastapi import WebSocket, WebSocketDisconnect
from strands.experimental.bidi.agent import BidiAgent
from strands.experimental.bidi.models.nova_sonic import BidiNovaSonicModel

async def handle_websocket_session(websocket: WebSocket):
    try:
        # 1. Receive config from frontend
        config = await websocket.receive_json()

        # 2. Voice-optimized system prompt (migrated from text agent)
        system_prompt = config.get("system_prompt", "You are a helpful voice assistant.")

        # 3. Create BidiAgent with Nova Sonic
        model = BidiNovaSonicModel(
            region=config.get("region", "us-east-1"),
            model_id="amazon.nova-2-sonic-v1:0",
            provider_config={
                "audio": {
                    "input_sample_rate": 16000,
                    "output_sample_rate": 16000,
                    "voice": config.get("voice", "matthew"),
                }
            },
        )
        agent = BidiAgent(model=model, tools=[], system_prompt=system_prompt)

        # 4. Input handler — routes text and audio from frontend
        async def handle_input():
            while True:
                message = await websocket.receive_json()
                if message.get("type") == "text_input":
                    await agent.send(message.get("text", ""))
                    continue
                return message  # audio frame

        # 5. Run bidirectional streaming
        await agent.run(inputs=[handle_input], outputs=[websocket.send_json])

    except WebSocketDisconnect:
        pass
```

### Adding Tools to the Voice Agent

Tools from the text agent can be passed directly to BidiAgent using Strands `@tool` decorators. The tool logic stays the same — just pass them to the agent:

```python
from strands import tool

@tool
def get_balance(account_id: str) -> str:
    """Get account balance for the given account ID.

    Args:
        account_id: The customer account identifier
    """
    # Same logic as your text agent's tool
    result = your_existing_function(account_id)
    return json.dumps(result)

# Pass tools to BidiAgent
agent = BidiAgent(
    model=model,
    tools=[get_balance],  # list of @tool-decorated functions
    system_prompt=system_prompt,
)
```

If you have many tools or want to use MCP servers, pass them via `mcp_gateway_arn`:

```python
model = BidiNovaSonicModel(
    region="us-east-1",
    model_id="amazon.nova-2-sonic-v1:0",
    provider_config={"audio": {"input_sample_rate": 16000, "output_sample_rate": 16000, "voice": "matthew"}},
    mcp_gateway_arn=["arn:aws:bedrock-agentcore:us-east-1:123456:gateway/GW1"],
)
```

For the full orchestrator reference (large-event splitting, observability), see [references/server-reference.md](references/server-reference.md).

---

## Project Structure

```
your-voice-agent/
├── server.py           # FastAPI WebSocket server (Part 2)
├── agent.py            # BidiAgent session handler + voice prompt (Part 2)
├── tools.py            # @tool-decorated functions (migrated from text agent)
├── client.py           # Python client that serves the HTML frontend
├── client.html         # Browser-based WebSocket client with mic/speaker
├── requirements.txt    # Python dependencies
└── README.md           # Setup and run instructions
```

## Generated Client

Always generate a client alongside the server. The client is a simple Python HTTP server that serves an HTML page with WebSocket audio streaming.

### client.py

```python
#!/usr/bin/env python3
"""Serves the HTML client and connects to the voice agent WebSocket server."""

import argparse
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

class ClientHandler(BaseHTTPRequestHandler):
    ws_url = None

    def do_GET(self):
        html_path = os.path.join(os.path.dirname(__file__), "client.html")
        with open(html_path, "r") as f:
            content = f.read()
        if self.ws_url:
            content = content.replace("ws://localhost:8080/ws", self.ws_url)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(content.encode())

    def log_message(self, format, *args):
        pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ws-url", default="ws://localhost:8080/ws",
                        help="WebSocket server URL (default: ws://localhost:8080/ws)")
    parser.add_argument("--port", type=int, default=8000,
                        help="HTTP server port for the client (default: 8000)")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    ClientHandler.ws_url = args.ws_url
    httpd = HTTPServer(("", args.port), ClientHandler)
    url = f"http://localhost:{args.port}"
    print(f"Client: {url}")
    print(f"WebSocket: {args.ws_url}")
    if not args.no_browser:
        webbrowser.open(url)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
```

### client.html

Generate a minimal HTML client with:
- WebSocket connection to the server
- Config event sent on connect (voice, model_id, region, sample rates, system_prompt)
- Microphone capture via AudioContext at 16kHz, converted to int16 PCM, base64-encoded, sent as `{ type: "bidi_audio_input", audio, format: "pcm", sample_rate: 16000, channels: 1 }`
- Audio playback of received `bidi_audio_stream` base64 PCM chunks
- Text input fallback with a send button
- Transcript display for user and assistant messages

The HTML client should follow the patterns from Part 1 (Frontend). For a complete production-ready implementation, see `strands/client/strands-client.html` in this repo.

## Generated README

When creating the voice agent, always generate a `README.md` with setup instructions including Python venv:

```markdown
# [Agent Name] Voice Agent

Real-time voice agent using Strands BidiAgent with Amazon Nova Sonic.

## Setup

### System Dependencies

macOS:
\```bash
brew install portaudio
\```

Ubuntu/Debian:
\```bash
sudo apt-get install -y portaudio19-dev gcc g++ make
\```

### Python Environment

\```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
\```

### Environment Variables

\```bash
# Set any required tool/service ARNs or API keys
export AWS_DEFAULT_REGION=us-east-1
\```

### Run

\```bash
source .venv/bin/activate
python server.py
\```

The WebSocket server starts on port 8080 by default. To use a different port:

\```bash
python server.py --port 9000
# or
PORT=9000 python server.py
\```

### Connect the Client

Open a second terminal:

\```bash
source .venv/bin/activate
python client.py --ws-url ws://localhost:8080/ws
\```

This opens a browser with mic/speaker controls. If you changed the server port, update the URL accordingly:

\```bash
python client.py --ws-url ws://localhost:9000/ws
\```
```

---

## Examples

Three complete before/after migration examples in `examples/`:

- **[examples/langchain-migration/](examples/langchain-migration/)** — LangChain `create_react_agent` → BidiAgent + Nova Sonic
- **[examples/openai-migration/](examples/openai-migration/)** — OpenAI function-calling → BidiAgent + Nova Sonic
- **[examples/custom-migration/](examples/custom-migration/)** — Bedrock Converse → BidiAgent + Nova Sonic

Each contains `text_agent.py` (before), `voice_agent.py` (after), and a README.

## Common Pitfalls

- **Long system prompts**: Keep the voice prompt under ~500 words. Move detailed tool instructions into tool descriptions.
- **JSON in tool results**: Nova Sonic will try to read JSON aloud. Return clean natural-language strings from tools.
- **Sample rate**: Nova Sonic requires 16kHz. A mismatch produces garbled audio with no error.
- **WebSocket message size**: Use `split_large_event` from `strands/websocket/server.py` for large audio payloads.
- **Missing portaudio**: The `pyaudio` package requires the `portaudio` system library. Install it before `pip install`.
