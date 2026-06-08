# Claude to Nova 2 Lite Feature Mapping

Covers both source surfaces: the **Anthropic Messages API** (`anthropic` SDK → `api.anthropic.com`) and **Claude on Bedrock** (`boto3` `converse` with a Claude `modelId`). The Bedrock-source path skips the SDK/auth rows — see the notes inline.

## SDK & Client Initialization

| Claude (Anthropic Messages API) | Nova 2 Lite (Bedrock) |
|--------|----------------------|
| `from anthropic import Anthropic` | `import boto3` |
| `client = Anthropic(api_key=...)` | `client = boto3.client("bedrock-runtime", region_name="us-east-1")` |
| `AsyncAnthropic(...)` | `boto3` is sync; wrap in a thread executor or use `aioboto3` |
| `AnthropicBedrock(...)` (Claude via Bedrock SDK) | `boto3.client("bedrock-runtime")` — drop the Anthropic wrapper |
| `client.messages.create(...)` | `client.converse(...)` |
| API key auth (`ANTHROPIC_API_KEY` / `x-api-key`) | AWS credentials (IAM role, profile, or env vars) |

> **Claude-on-Bedrock source:** the client is already `boto3.client("bedrock-runtime")` and the call is already `converse`. No SDK or auth change — only the `modelId`, reasoning config, and prompt change.

## Model IDs

Nova 2 Lite requires a region-prefixed model ID. Ask the user which region to use:

| Model ID | Region |
|----------|--------|
| `us.amazon.nova-2-lite-v1:0` | US (default) |
| `eu.amazon.nova-2-lite-v1:0` | EU |
| `jp.amazon.nova-2-lite-v1:0` | Japan |
| `global.amazon.nova-2-lite-v1:0` | Cross-region |

**Claude → Nova mapping (default US):**

| Claude Model | Nova Model ID | Note |
|--------------|---------------------|------|
| `claude-3-haiku` | `us.amazon.nova-2-lite-v1:0` | Direct replacement for most workloads |
| `claude-3-5-haiku` | `us.amazon.nova-2-lite-v1:0` | Benchmark parity; Nova adds video input |
| `claude-haiku-4-5` | `us.amazon.nova-2-lite-v1:0` | Confirm the marginal quality edge justifies Claude's higher cost before migrating |
| `claude-3-sonnet` | `us.amazon.nova-2-lite-v1:0` | Validate with task benchmarks; enable extended thinking at medium |
| `claude-3-5-sonnet` | `us.amazon.nova-2-lite-v1:0` — **ask user to confirm they have evaluated Nova 2 Lite for their use case before proceeding** | Test aggressively with representative workloads |

## System Prompt

| Claude | Nova 2 Lite |
|--------|-------------|
| Top-level `system="..."` (string) | `system=[{"text": "..."}]` (block array) |
| Top-level `system=[{"type":"text","text":"..."}]` (blocks) | `system=[{"text": "..."}]` (drop the `type` key) |
| Full instructions allowed for all modalities | **MULTIMODAL RESTRICTION**: System prompt limited to persona + response style only. All task instructions MUST go in the user message. |

> Both APIs use a top-level `system` field (not a message role). The change is the block shape: Anthropic allows a bare string or `{"type":"text",...}`; Bedrock requires `{"text": ...}`.

## Messages / Content

| Claude | Nova 2 Lite |
|--------|-------------|
| `messages=[{"role":"user","content":"Hello"}]` (string shorthand) | `messages=[{"role":"user","content":[{"text":"Hello"}]}]` |
| `content=[{"type":"text","text":"..."}]` | `content=[{"text":"..."}]` (drop `type`) |
| `{"role":"assistant", ...}` | `{"role":"assistant", ...}` (same — no rename needed, unlike Gemini) |
| Multi-turn: pass full `messages` history | Same — pass full `messages` history |

## Tool Use / Function Calling

| Claude | Nova 2 Lite |
|--------|-------------|
| `tools=[{"name","description","input_schema":{...}}]` | `toolConfig={"tools":[{"toolSpec":{"name","description","inputSchema":{"json":{...}}}}]}` |
| `input_schema` (JSON Schema) | `inputSchema.json` (JSON Schema — usually a 1:1 lift) |
| `tool_choice={"type":"auto"/"any"/"tool","name":...}` | `toolChoice={"auto":{}}` / `{"any":{}}` / `{"tool":{"name":...}}` |
| Response: `content` block `{"type":"tool_use","id","name","input"}` | Response: `{"toolUse":{"toolUseId","name","input"}}` block |
| Stop: `stop_reason == "tool_use"` | Stop: `stopReason == "tool_use"` |
| Send back: `{"type":"tool_result","tool_use_id","content"}` | `{"toolResult":{"toolUseId","content":[{"text":...}]}}` |

## Structured Output

| Claude | Nova 2 Lite |
|--------|-------------|
| Tool-forcing via `tool_choice={"type":"tool","name":...}` | Same idea — `toolChoice={"tool":{"name":...}}` with schema in `inputSchema.json` |
| Prompt-based JSON ("respond only in JSON") | Inline schema in prompt + `temperature=0` (simple, ≤10 keys) |
| — | Tool-forcing for complex schemas (>10 keys) |

## Extended Thinking / Reasoning

**Which Claude models support native thinking:**
- Claude 3 Haiku / 3.5 Haiku: **NO** native thinking. Any reasoning is prompt-based CoT.
- Claude 3.5 Sonnet / Haiku 4.5: **YES** — `thinking={"type":"enabled","budget_tokens":N}`.

| Claude | Nova 2 Lite |
|--------|-------------|
| `thinking={"type":"enabled","budget_tokens":N}` | `additionalModelRequestFields={"reasoningConfig":{"type":"enabled","maxReasoningEffort":"medium"}}` |
| No `thinking` param (disabled) | Omit `additionalModelRequestFields` entirely |
| CoT prompting ("think step by step") | Keep prompt text as-is, reasoning disabled — or enable `reasoningConfig` and drop the CoT text |
| `thinking` content blocks in response | `reasoningContent` blocks in response content |
| Compatible with streaming | **NOT** compatible with streaming on Nova |

**Effort translation — ask the user.** Do NOT copy Claude's `budget_tokens` directly — the models have different reasoning efficiency. Present these Nova options:

| Nova Effort | Config |
|-------------|--------|
| `low` | `{"reasoningConfig":{"type":"enabled","maxReasoningEffort":"low"}}` |
| `medium` | `{"reasoningConfig":{"type":"enabled","maxReasoningEffort":"medium"}}` |
| `high` | `{"reasoningConfig":{"type":"enabled","maxReasoningEffort":"high"}}` — **MUST omit `inferenceConfig`** entirely and extend client read timeout |

## Inference Config

| Claude (top-level) | Nova 2 Lite (nested in `inferenceConfig`) |
|--------|-------------|
| `max_tokens` (required by Anthropic) | `inferenceConfig.maxTokens` (optional; max 65,536) |
| `temperature` | `inferenceConfig.temperature` |
| `top_p` | `inferenceConfig.topP` |
| `stop_sequences` | `inferenceConfig.stopSequences` |
| `top_k` | Not directly supported — may go in `additionalModelRequestFields` |

## Streaming

| Claude | Nova 2 Lite |
|--------|-------------|
| `client.messages.create(..., stream=True)` or `client.messages.stream(...)` | `client.converse_stream(...)` (separate method) |
| Iterate events: `message_start`, `content_block_delta`, `message_stop` | Event types: `contentBlockStart`, `contentBlockDelta`, `contentBlockStop`, `messageStop` |
| `event.delta.text` | `event["contentBlockDelta"]["delta"]["text"]` |

## Multimodal Content

| Claude | Nova 2 Lite |
|--------|-------------|
| Image: `{"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":...}}` | `{"image":{"format":"jpeg","source":{"bytes": image_bytes}}}` |
| Image via URL `source.type="url"` | Inline bytes, or `{"image":{...,"source":{"s3Location":{"uri":"s3://..."}}}}` |
| Document: `{"type":"document","source":{...}}` | `{"document":{"format":"pdf","name":"...","source":{"bytes":...}}}` |
| Supports: JPEG, PNG, GIF, WebP (images); PDF | Supports: JPEG, PNG, GIF, WebP (images); PDF (documents); MP4, MKV, MOV, WebM, etc. (video — Claude has no video) |
| Image blocks use `type` key; base64 string | Image blocks use `image` key; binary bytes + explicit `format` |
| No media-ordering constraint | Media MUST precede text in content array |
| System instructions work normally | System prompt restricted to persona only |

## Prompt Structure

| Claude | Nova 2 Lite |
|--------|-------------|
| XML tags (`<document>`, `<instructions>`, `<thinking>`), markdown, free-form | `##Section Name##` delimiters (NOT XML tags) |
| `<context>...</context>` | `##Context Information:##` |
| `<task>...</task>` | `##Task Summary:##` |
| `<instructions>...</instructions>` | `##Model Instructions:##` |
| Tolerant of vague phrasing | Explicit task + format + constraints required for best quality |
| Few-shot examples inline | Express as role-tagged `messages[]` turns where practical |

## Features Without Direct Equivalent

| Claude Feature | Nova 2 Lite Alternative |
|----------------|------------------------|
| Audio input | Not supported — pre-transcribe with Amazon Transcribe; pair with Nova Sonic (conversational) or Amazon Polly (TTS) |
| Image generation | Not in Nova Lite — use Amazon Nova Canvas |
| `cache_control` prompt-caching blocks | Bedrock prompt caching (different API surface) |
| Computer use / managed tool runtimes | Build with tool use + orchestration (e.g., Bedrock AgentCore) |
| Web access via Anthropic tooling | `amazon.nova_grounding` built-in tool (US Regions; needs `bedrock:InvokeTool`) |
| Code execution via Anthropic tooling | `amazon.nova_code_interpreter` built-in tool (us-east-1, us-west-2, ap-northeast-1) |

## Error Mapping

| Condition | Claude (Anthropic SDK) | Nova 2 Lite (Bedrock Converse) |
|-----------|------------------------|-------------------------------|
| Rate limit / quota | `RateLimitError` | `ThrottlingException` |
| Invalid request | `BadRequestError` | `ValidationException` |
| Auth / permission | `AuthenticationError` / `PermissionDeniedError` | `AccessDeniedException` |
| Not found | `NotFoundError` | `ResourceNotFoundException` |
| Server error | `APIError` / `InternalServerError` | `InternalServerError` |
| Timeout | request-level timeout | `botocore.ReadTimeoutError` / `ModelTimeoutException` (tune `read_timeout`) |
