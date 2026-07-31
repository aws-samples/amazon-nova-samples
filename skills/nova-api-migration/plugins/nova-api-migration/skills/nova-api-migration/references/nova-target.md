# Amazon Nova 2 Lite — Shared API Migration Target

This is the **target side** of every API migration. The source-specific guide (`gemini/`, `openai/`, `claude/`) tells you how to read the original code; this file tells you what to produce on the Nova side. Every source guide points here so these rules are written once.

## Model IDs

Nova 2 Lite requires a region-prefixed model ID. **Ask the user which region to use**; default to `us.amazon.nova-2-lite-v1:0` if unspecified.

| Model ID | Region |
|----------|--------|
| `us.amazon.nova-2-lite-v1:0` | US (us-east-1, us-west-2) — default |
| `eu.amazon.nova-2-lite-v1:0` | EU (eu-west-1, etc.) |
| `jp.amazon.nova-2-lite-v1:0` | Japan (ap-northeast-1) |
| `global.amazon.nova-2-lite-v1:0` | Cross-region inference |

## Request Shape (Bedrock Converse API)

Every Nova call uses `boto3` `bedrock-runtime` `converse` (or `converse_stream`):

```python
import boto3
from botocore.config import Config

client = boto3.client("bedrock-runtime", region_name="us-east-1", config=Config(read_timeout=300))

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "..."}],
    messages=[{"role": "user", "content": [{"text": "..."}]}],
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
    # toolConfig=...,                      # when tools are used
    # additionalModelRequestFields=...,    # ONLY when reasoning enabled
)
text = response["output"]["message"]["content"][0]["text"]
```

Invariants that hold regardless of source provider:
- **Content is always typed blocks**: `[{"text": ...}]`, never a bare string.
- **Roles are `user` / `assistant`** (never `model`, never `system` as a role).
- **System prompt is a top-level block array**: `system=[{"text": "..."}]`.
- **Inference params are nested + camelCase**: `maxTokens`, `topP`, `stopSequences` inside `inferenceConfig`.
- **Media precedes text** in any multimodal content array.
- **Max output tokens** cap is 65,536.

## Inference Config by Use Case

Pick the inference config from the use-case type, not from the source model's defaults.

**Text / Agentic:**
| Use Case | Temperature | Top P | Reasoning |
|----------|------------|-------|-----------|
| `general` | 0.7 | default | DISABLED |
| `tool_calling` | 0.7 | 0.9 | DISABLED |
| `tool_calling_reasoning` | 1 | 0.9 | ENABLED |
| `complex_reasoning` | 0.7 | default | ENABLED |

**Multimodal:**
| Use Case | Temperature | Reasoning |
|----------|------------|-----------|
| OCR | 0.7 | DISABLED |
| Key information extraction | 0 | OPTIONAL |
| Object/UI detection | 0 | DISABLED |
| Video/Document summary/caption | 0 | OPTIONAL |
| Video timestamps/classification | 0 | DISABLED |

## Reasoning / Extended Thinking

Reasoning is **disabled by default** — omit `additionalModelRequestFields` entirely unless the source genuinely uses native reasoning. When the source has thinking enabled, ask the user which effort level to use:

| Nova Effort | Config |
|-------------|--------|
| `low` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "low"}}` |
| `medium` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}}` |
| `high` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "high"}}` |

Rules:
- **Default to disabled.** Enable `low` first only if evaluation shows quality gaps; escalate to `medium`/`high` sparingly.
- **Do NOT copy the source model's token budget** (Gemini `thinking_budget`, Claude `budget_tokens`, OpenAI `reasoning_effort`) directly — reasoning efficiency differs across models. Present the three Nova options and let the user choose.
- **At `high` effort:** you **MUST omit `inferenceConfig` entirely** — `temperature`, `topP`, `topK`, and `maxTokens` are rejected as a `ValidationException`. Also extend the client read timeout: `Config(read_timeout=3600)`. At `low`/`medium`, `inferenceConfig` works normally.
- **Reasoning is not compatible with streaming.**

## Tool Use (Target Shape)

Nova uses a single tool interface. Built-in and custom tools declare into the same list:

```python
toolConfig = {
    "tools": [
        {"toolSpec": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "inputSchema": {"json": {
                "type": "object",
                "properties": {"location": {"type": "string", "description": "City name"}},
                "required": ["location"],
            }},
        }},
    ],
    "toolChoice": {"auto": {}},   # or {"any": {}} or {"tool": {"name": "..."}}
}
```

- Response tool call is a `toolUse` content block; stop condition is `stopReason == "tool_use"`.
- Send results back as a `toolResult` content block in a `user` turn.
- Reference tools by name in the system prompt: `Use the 'tool_name' tool for X`.
- Keep tool descriptions to 20–50 words; parameter descriptions to ~10 words.

## Structured Output

- **Simple JSON (≤10 keys):** inline schema in the prompt + `temperature=0`.
- **Complex JSON (>10 keys):** tool-forcing — schema in `toolSpec.inputSchema.json` + `toolChoice={"tool": {"name": "..."}}` ; read the result from the `toolUse` block's `input`.

## Built-in Tools

- **`amazon.nova_grounding`** — real-time web info with citations. US Regions only. Requires `bedrock:InvokeTool` permission.
- **`amazon.nova_code_interpreter`** — runs Python in isolated sandboxes. us-east-1, us-west-2, ap-northeast-1. Requires `InvokeTool` permission.

## Multimodal Content

| Modality | Nova content block | Supported formats |
|----------|--------------------|-------------------|
| Image | `{"image": {"format": "...", "source": {"bytes": ...}}}` | JPEG, PNG, GIF, WebP |
| Document | `{"document": {"format": "pdf", "name": "...", "source": {"bytes": ...}}}` | PDF |
| Video | `{"video": {"format": "...", "source": {"bytes": ...}}}` | MP4, MKV, MOV, WebM, FLV, MPEG, MPG, WMV, 3GP |

- Source can be inline `bytes` or `{"s3Location": {"uri": "s3://..."}}`.
- Convert provider-specific URIs (`gs://`, Anthropic base64/URL, OpenAI URLs) to bytes or S3.
- Specify `format` explicitly.
- **Nova 2 Lite does not accept audio input** — pre-transcribe with Amazon Transcribe; pair with Amazon Nova Sonic for conversational voice.

## Streaming

Use `client.converse_stream()` instead of `client.converse()`:

```python
response = client.converse_stream(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "..."}]}],
    inferenceConfig={"temperature": 0.7},
)
for event in response["stream"]:
    if "contentBlockDelta" in event:
        text = event["contentBlockDelta"]["delta"].get("text", "")
        print(text, end="")
```

## Error Types (Bedrock Converse)

| Condition | Bedrock exception |
|-----------|-------------------|
| Rate limit / quota | `ThrottlingException` |
| Invalid request shape | `ValidationException` |
| Auth / permission | `AccessDeniedException` |
| Not found | `ResourceNotFoundException` |
| Server error | `InternalServerError` |
| Timeout | `botocore.ReadTimeoutError` / `ModelTimeoutException` |

## Validation Checklist (Run Before Presenting Any Migration)

- [ ] `additionalModelRequestFields` omitted when reasoning disabled; contains `reasoningConfig` when enabled
- [ ] At high effort: `inferenceConfig` omitted entirely and `read_timeout` extended
- [ ] Inference config matches the use-case table
- [ ] Content wrapped in typed blocks; roles are `user`/`assistant`; `system` is a block array
- [ ] Inference params nested in `inferenceConfig` with camelCase
- [ ] Multimodal: media precedes text in the content array
- [ ] Media converted to bytes/S3 with explicit `format`
- [ ] Tool schemas use `toolSpec` with `inputSchema.json`; `toolChoice` mapped correctly
- [ ] Error handling updated to Bedrock exception types
- [ ] No source-provider-specific surface remains (see the source guide's "what cannot migrate")
- [ ] System prompt extracted from messages into the top-level `system` parameter
