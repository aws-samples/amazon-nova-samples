# OpenAI to Nova 2 Lite Feature Mapping

## SDK & Client Initialization

| OpenAI | Nova 2 Lite (Bedrock) |
|--------|----------------------|
| `from openai import OpenAI` | `import boto3` |
| `client = OpenAI(api_key=...)` | `client = boto3.client("bedrock-runtime")` |
| `client.chat.completions.create(...)` | `client.converse(...)` |
| `client.responses.create(...)` | `client.converse(...)` |
| `client.beta.assistants.create(...)` / threads | `client.converse(...)` + external state |
| API key auth (`OPENAI_API_KEY`, bearer token) | AWS credentials (IAM role, profile, or env vars) |

In production, prefer IAM roles attached to compute resources over static keys.

## Model IDs

Nova 2 Lite requires a region-prefixed model ID. Ask the user which region to use:

| Model ID | Region |
|----------|--------|
| `us.amazon.nova-2-lite-v1:0` | US (default) |
| `eu.amazon.nova-2-lite-v1:0` | EU |
| `jp.amazon.nova-2-lite-v1:0` | Japan |
| `global.amazon.nova-2-lite-v1:0` | Cross-region |

**OpenAI → Nova mapping (default US):**

| OpenAI Model | Migration Complexity | Nova Model ID |
|--------------|---------------------|---------------------|
| `gpt-4o-mini` | Low | `us.amazon.nova-2-lite-v1:0` |
| `gpt-4o` (multimodal) | Low-Medium | `us.amazon.nova-2-lite-v1:0` — supports text, image, and video input |
| `gpt-4.1` / `gpt-4.1-mini` | Low-Medium | `us.amazon.nova-2-lite-v1:0` — both have 1M context; Nova adds extended thinking + built-in tools |
| `gpt-5-mini` / `gpt-5-nano` | Low | `us.amazon.nova-2-lite-v1:0` |
| `gpt-5.2` | Medium | `us.amazon.nova-2-lite-v1:0` — enable extended thinking for reasoning parity |
| `o1` / `o3` (reasoning) | Medium | `us.amazon.nova-2-lite-v1:0` — **ask user to confirm they have evaluated Nova 2 Lite before proceeding; Nova 2 Pro exists if Lite at high effort falls short** |
| `gpt-4` / `gpt-3.5-turbo` | Low | `us.amazon.nova-2-lite-v1:0` — legacy, straightforward |

**Decision rule:** Start every migration with Nova 2 Lite, reasoning disabled. Enable extended thinking at `low` first only if evaluation shows quality gaps, then increase to `medium`/`high` as needed.

## Authentication

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `OpenAI(api_key="sk-...")` or `OPENAI_API_KEY` env var | AWS credentials resolved by boto3 (IAM role, `~/.aws/credentials`, env vars) |
| Bearer token in request header | IAM SigV4 signing (handled by boto3) |
| Per-key rate limits | Per-account service quotas; throttling via `ThrottlingException` |

## System Prompt

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `{"role": "system", "content": "..."}` as the first message | `system=[{"text": "..."}]` as a separate top-level parameter |
| Full instructions allowed for all modalities | **MULTIMODAL RESTRICTION**: System prompt limited to persona + response style only. All task instructions MUST go in the user message. |
| Sent inside `messages` | Extract from `messages` during migration |

## Messages / Content

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `messages=[{"role": "user", "content": "text"}]` | `messages=[{"role": "user", "content": [{"text": "text"}]}]` |
| `content` is a flat string | `content` is a list of typed blocks |
| `{"type": "text", "text": "..."}` (multimodal form) | `{"text": "..."}` |
| `{"type": "image_url", "image_url": {"url": "data:..."}}` | `{"image": {"format": "png", "source": {"bytes": ...}}}` |
| Image as URL or base64 data URI | Image as raw binary bytes |
| `role: "assistant"` / `role: "user"` | Same roles; content must be typed blocks |
| `role: "tool"` (tool result message) | `{"role": "user", "content": [{"toolResult": {...}}]}` |
| Media can be anywhere in content | Media MUST come before text in the content array |

## Inference Parameters

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `max_tokens` (top-level) | `inferenceConfig.maxTokens` (max 65,536) |
| `max_completion_tokens` (newer) | `inferenceConfig.maxTokens` |
| `temperature` (top-level) | `inferenceConfig.temperature` |
| `top_p` (top-level) | `inferenceConfig.topP` |
| `stop` (top-level) | `inferenceConfig.stopSequences` |
| `n` (multiple completions) | Not supported (always 1) |
| `frequency_penalty` / `presence_penalty` | Not directly supported |
| `seed` | Not supported |

## Function Calling / Tool Use

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `tools=[{"type": "function", "function": {...}}]` | `toolConfig={"tools": [{"toolSpec": {...}}]}` |
| `function.name` | `toolSpec.name` |
| `function.description` | `toolSpec.description` |
| `function.parameters` (JSON Schema) | `toolSpec.inputSchema.json` (JSON Schema — re-wrap, structurally compatible) |
| `tool_choice="auto"` | `toolChoice={"auto": {}}` |
| `tool_choice="required"` | `toolChoice={"any": {}}` |
| `tool_choice={"type": "function", "function": {"name": "x"}}` | `toolChoice={"tool": {"name": "x"}}` |
| `tool_choice="none"` | Omit `toolConfig`, or instruct the model not to call tools |
| Response: `message.tool_calls[].function` | Response: `toolUse` content block |
| Send back: `{"role": "tool", "tool_call_id": ..., "content": ...}` | Send back: `{"role": "user", "content": [{"toolResult": {"toolUseId": ..., "content": [...]}}]}` |

OpenAI's function `parameters` use JSON Schema, the same format Nova expects in `inputSchema.json` — the schema body usually copies over directly; only the wrapper structure changes.

## Structured Output

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `response_format={"type": "json_object"}` (JSON mode) | Inline schema in prompt + `temperature=0` |
| `response_format={"type": "json_schema", "json_schema": {...}}` (Structured Outputs) | Tool-forcing: schema in `toolSpec.inputSchema` + `toolChoice={"tool": {"name": ...}}` |
| `response_format=<PydanticModel>` (SDK helper) | Convert Pydantic `.model_json_schema()` to `toolSpec.inputSchema.json` |
| Schema enforced natively | Schema enforced via tool-forcing (complex) or prompt instruction (simple) |

Rule of thumb: simple JSON (≤10 keys) → inline schema in prompt; complex JSON (>10 keys) → tool-forcing.

## Reasoning / Extended Thinking

**Which OpenAI models support reasoning effort:**
- `gpt-4o` / `gpt-4o-mini` / `gpt-4.1` / `gpt-4` / `gpt-3.5-turbo`: NO native reasoning. Any reasoning is prompt-based CoT.
- `gpt-5` / `gpt-5.2` / `o1` / `o3`: YES — `reasoning_effort` parameter.

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `reasoning_effort="low"/"medium"/"high"` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "low"/"medium"/"high"}}` |
| `reasoning_effort="minimal"` or omitted | Omit `additionalModelRequestFields` entirely (disabled) |
| Reasoning summary in response | `reasoningContent` blocks in response content (reasoning text appears as `[REDACTED]`) |
| Default: model-dependent | Default: disabled — omit `additionalModelRequestFields` |

**Effort translation — ask the user:**

Do NOT map OpenAI's effort name directly to Nova's. The scales are not numerically equivalent. Present these Nova options and let the user choose:

| Nova Effort | Config | Constraint |
|-------------|--------|-----------|
| `low` | `{"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "low"}}` | Start here; keep `inferenceConfig` |
| `medium` | `{"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}}` | Keep `inferenceConfig` |
| `high` | `{"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "high"}}` | **MUST omit `inferenceConfig`** entirely (no temperature, topP, maxTokens, topK) and set client `read_timeout=3600`. May produce >65K output (up to 128K). |

You are charged for reasoning tokens because they contribute to output quality. Reasoning content is returned as the literal string `[REDACTED]` in the `reasoningContent.reasoningText.text` field — Nova 2 does not expose the reasoning text today. Extended thinking is supported alongside tool calling.

## Streaming

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `client.chat.completions.create(..., stream=True)` | `client.converse_stream(...)` (separate method) |
| Iterate: `for chunk in response: chunk.choices[0].delta.content` | Event types: `messageStart`, `contentBlockStart`, `contentBlockDelta`, `contentBlockStop`, `messageStop` |
| `chunk.choices[0].delta.content` | `event["contentBlockDelta"]["delta"]["text"]` |

## Multimodal Content

| OpenAI | Nova 2 Lite |
|--------|-------------|
| Images via `image_url` (URL or base64 data URI) | Images via `{"image": {"format": "...", "source": {"bytes": ...}}}` — raw bytes |
| No video input (text models) | Video via `{"video": {"format": "...", "source": {"bytes": ...}}}` |
| Documents via Assistants file upload | Documents via `{"document": {"format": "pdf", "name": "...", "source": {"bytes": ...}}}` |
| Supports: JPEG, PNG, GIF, WebP | Images: JPEG, PNG, GIF, WebP; Documents: PDF; Video: MP4, MKV, MOV, WebM, FLV, MPEG, MPG, WMV, 3GP |
| No ordering constraint | Media MUST precede text in content array |
| System instructions work normally | System prompt restricted to persona only |

## Prompt Structure

| OpenAI | Nova 2 Lite |
|--------|-------------|
| Free-form, markdown, or loosely phrased | `##Section Name##` delimiters with explicit structure |
| Instructions inline in one block | Separate `##Task Summary:##`, `##Context Information:##`, `##Model Instructions:##`, `##Response style and format requirements:##` |
| Tolerates vague phrasing | Higher quality with explicit task / input / format / constraints |

## Error Handling

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `openai.RateLimitError` | `ThrottlingException` |
| `openai.APIError` | `ValidationException` |
| `openai.APITimeoutError` | `ModelTimeoutException` |
| `openai.AuthenticationError` | `AccessDeniedException` (IAM) |
| `openai.BadRequestError` | `ValidationException` |

Catch via `botocore.exceptions.ClientError` and branch on `error.response["Error"]["Code"]`.

## Features Without Direct Equivalent

| OpenAI Feature | Nova 2 Lite Alternative |
|----------------|------------------------|
| Assistants API threads / persistent state | Manage conversation history externally; pass full `messages` each call |
| Assistants code interpreter | Nova `nova_code_interpreter` built-in tool |
| Assistants file search / retrieval | Amazon Bedrock Knowledge Bases |
| Web search tool | Nova `nova_grounding` built-in web grounding tool |
| Image generation (DALL-E / `gpt-image`) | Amazon Nova Canvas (separate model) |
| Text-to-speech / Whisper transcription | Amazon Polly / Amazon Transcribe |
| Realtime API (voice) | Amazon Nova Sonic |
| Fine-tuned models | Re-run customization on Nova via Amazon Bedrock |
| `n` > 1 (multiple completions) | Not supported — make multiple calls |
| `seed` (deterministic sampling) | Not supported |
