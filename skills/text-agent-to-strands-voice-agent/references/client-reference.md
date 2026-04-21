# Client Implementation Reference

Detailed reference for the browser and Python CLI clients. For the minimal version, see SKILL.md Step 3.

## Browser Client

The browser client uses Web Audio API to capture microphone input, stream it as base64-encoded PCM over WebSocket, and play back audio responses. The full implementation is in `strands/client/strands-client.html`.

### Audio Capture with AudioWorklet

The AudioWorklet runs in a separate thread for low-latency PCM capture:

```javascript
class PCMProcessor extends AudioWorkletProcessor {
    process(inputs) {
        const input = inputs[0][0];
        if (input) {
            const pcm = new Int16Array(input.length);
            for (let i = 0; i < input.length; i++) {
                pcm[i] = Math.max(-32768, Math.min(32767, input[i] * 32768));
            }
            this.port.postMessage(pcm.buffer);
        }
        return true;
    }
}
registerProcessor('pcm-processor', PCMProcessor);
```

The main thread converts PCM buffers to base64 and sends them over WebSocket:

```javascript
workletNode.port.onmessage = (event) => {
    const base64 = arrayBufferToBase64(event.data);
    ws.send(JSON.stringify({ type: "audio", audio: base64 }));
};
```

### Audio Playback

Incoming audio chunks are scheduled for gapless playback:

```javascript
let nextPlayTime = 0;

function playAudioChunk(base64Audio) {
    const pcm = base64ToInt16Array(base64Audio);
    const float32 = new Float32Array(pcm.length);
    for (let i = 0; i < pcm.length; i++) {
        float32[i] = pcm[i] / 32768;
    }

    const buffer = playbackCtx.createBuffer(1, float32.length, sampleRate);
    buffer.getChannelData(0).set(float32);

    const source = playbackCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(playbackCtx.destination);

    const now = playbackCtx.currentTime;
    const startTime = Math.max(now, nextPlayTime);
    source.start(startTime);
    nextPlayTime = startTime + buffer.duration;
}
```

### Event Handling

The server sends these event types:

| Event type | Fields | Action |
|-----------|--------|--------|
| `audio` | `audio` (base64) | Decode and play through speaker |
| `text` | `role`, `text` | Display transcript in conversation panel |
| `tool_use` | `name`, `input` | Show "Calling [tool]..." in UI |
| `tool_result` | `name`, `content` | Show tool completion |
| `system` | `message` | Show system message (config ack, errors) |
| `error` | `message` | Display error |

### Utility Functions

```javascript
function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

function base64ToInt16Array(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return new Int16Array(bytes.buffer);
}
```

## Python CLI Client

For testing without a browser. Uses `pyaudio` for mic capture and speaker playback.

```python
import asyncio, json, base64, pyaudio, websockets

RATE, CHANNELS, CHUNK = 16000, 1, 1024

async def run(url, system_prompt, gateway_arns=None):
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({
            "type": "config",
            "voice": "matthew",
            "model_id": "amazon.nova-2-sonic-v1:0",
            "input_sample_rate": RATE,
            "output_sample_rate": RATE,
            "system_prompt": system_prompt,
            "gateway_arns": gateway_arns or [],
        }))

        pa = pyaudio.PyAudio()
        mic = pa.open(format=pyaudio.paInt16, channels=CHANNELS,
                      rate=RATE, input=True, frames_per_buffer=CHUNK)
        spk = pa.open(format=pyaudio.paInt16, channels=CHANNELS,
                      rate=RATE, output=True, frames_per_buffer=CHUNK)

        async def send_audio():
            while True:
                data = mic.read(CHUNK, exception_on_overflow=False)
                await ws.send(json.dumps({
                    "type": "audio",
                    "audio": base64.b64encode(data).decode()
                }))
                await asyncio.sleep(0.01)

        async def recv_events():
            async for msg in ws:
                evt = json.loads(msg)
                if evt.get("type") == "audio" and "audio" in evt:
                    spk.write(base64.b64decode(evt["audio"]))
                elif evt.get("type") == "text":
                    print(f"[{evt.get('role','')}] {evt.get('text','')}")

        await asyncio.gather(send_audio(), recv_events())
```

### Running

```bash
pip install pyaudio websockets

# Local server
python client.py --ws-url ws://localhost:8080/ws

# Deployed via AgentCore Runtime (presigned URL)
python client.py --runtime-arn arn:aws:bedrock-agentcore:us-east-1:123456:runtime/RTID
```

## Migration Checklist

- [ ] System prompt is voice-optimized (see `references/voice-prompt-guide.md`)
- [ ] Gateway ARNs configured for all text agent tools
- [ ] Sample rates match the model (16kHz Nova Sonic, 24kHz OpenAI/Gemini)
- [ ] Text input fallback works for accessibility
- [ ] Audio playback is gapless (no clicks between chunks)
- [ ] Tool results are spoken naturally, not as raw JSON
- [ ] Agent greets, uses caller's name, and says goodbye
