# Claude → Nova 2 Lite API Feature Mapping

Covers both source surfaces: the **Anthropic Messages API** (`anthropic` SDK) and **Claude on Bedrock** (`boto3` `converse` with a Claude `modelId`).

## SDK & Client Initialization

| Claude (Anthropic Messages API) | Nova 2 Lite (Bedrock) |
|--------|----------------------|
| `from anthropic import Anthropic` | `import boto3` |
| `client = Anthropic(api_key=...)` | `client = boto3.client("bedrock-runtime", region_name="us-east-1")` |
| `AsyncAnthropic(...)` | `boto3` is sync; wrap in thread executor or use `aioboto3` |
| `AnthropicBedrock(...)` | `boto3.client("bedrock-runtime")` — drop the Anthropic wrapper |
| `client.messages.create(...)` | `client.converse(...)` |
| API key auth (`ANTHROPIC_API_KEY`) | AWS credentials (IAM role, profile, or env vars) |

> **Claude-on-Bedrock source:** the client is already `boto3.client("bedrock-runtime")` and the call is already `converse`. Only the `modelId`, reasoning config, and prompt change.

## Model IDs

| Claude Model | Nova Model ID | Note |
|--------------|---------------------|------|
| `claude-3-haiku` | `us.amazon.nova-2-lite-v1:0` | Direct replacement |
| `claude-3-5-haiku` | `us.amazon.nova-2-lite-v1:0` | Benchmark parity; Nova adds video |
| `claude-haiku-4-5` | `us.amazon.nova-2-lite-v1:0` | Confirm quality gap justifies cost |
| `claude-3-sonnet` / `claude-3-5-sonnet` | `us.amazon.nova-2-lite-v1:0` | **Ask user to confirm** evaluation |

## System Prompt

| Claude | Nova 2 Lite |
|--------|-------------|
| `system="..."` (string) | `system=[{"text": "..."}]` |
| `system=[{"type":"text","text":"..."}]` (blocks) | `system=[{"text": "..."}]` (drop `type`) |
| Full instructions for all modalities | **Multimodal**: persona-only; task instructions in user message |

> Both use a top-level `system` field. The change is block shape: Anthropic allows string or `{"type":"text",...}`; Bedrock requires `{"text": ...}`.

## Messages / Content

| Claude | Nova 2 Lite |
|--------|-------------|
| `"content": "Hello"` (string shorthand) | `"content": [{"text": "Hello"}]` (typed blocks required) |
| `"content": [{"type":"text","text":"..."}]` | `"content": [{"text": "..."}]` (drop `type`) |
| `{"role": "assistant", ...}` | `{"role": "assistant", ...}` (same — no rename) |
| Multi-turn: pass full `messages` history | Same |

## Inference Parameters

| Claude | Nova 2 Lite |
|--------|-------------|
| `max_tokens` (top-level, required) | `inferenceConfig={"maxTokens": ...}` |
| `temperature` (top-level) | `inferenceConfig={"temperature": ...}` |
| `top_p` (top-level) | `inferenceConfig={"topP": ...}` |
| `top_k` (top-level) | Not supported |
| `stop_sequences` (top-level) | `inferenceConfig={"stopSequences": [...]}` |

## Tool Use / Function Calling

| Claude | Nova 2 Lite |
|--------|-------------|
| `tools=[{"name", "description", "input_schema": {...}}]` | `toolConfig={"tools":[{"toolSpec":{"name", "description", "inputSchema":{"json":{...}}}}]}` |
| `input_schema` (JSON Schema) | `inputSchema.json` (JSON Schema — usually 1:1 lift) |
| `tool_choice={"type": "auto"}` | `toolChoice={"auto": {}}` |
| `tool_choice={"type": "any"}` | `toolChoice={"any": {}}` |
| `tool_choice={"type": "tool", "name": "X"}` | `toolChoice={"tool": {"name": "X"}}` |
| Response: `{"type":"tool_use","id","name","input"}` | `{"toolUse":{"toolUseId","name","input"}}` |
| `stop_reason == "tool_use"` | `stopReason == "tool_use"` |
| Send back: `{"type":"tool_result","tool_use_id","content"}` | `{"toolResult":{"toolUseId","content":[{"text":...}]}}` |

## Structured Output

| Claude | Nova 2 Lite |
|--------|-------------|
| Tool-forcing: `tool_choice={"type":"tool","name":"..."}` | `toolChoice={"tool":{"name":"..."}}` with schema in `inputSchema.json` |
| Prompt-based JSON ("respond only in JSON") | Inline schema in prompt + `temperature=0` (simple, ≤10 keys) |

## Extended Thinking / Reasoning

| Claude | Nova 2 Lite |
|--------|-------------|
| `thinking={"type":"enabled","budget_tokens":N}` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "..."}}` |
| `thinking={"type":"disabled"}` / omit | Omit `additionalModelRequestFields` entirely |
| `thinking` blocks in response | `reasoningContent` blocks in response |
| Claude 3/3.5 Haiku: no native thinking | Default disabled |
| Claude 3.5 Sonnet / Haiku 4.5: yes | Map to Nova effort level |

## Streaming

| Claude | Nova 2 Lite |
|--------|-------------|
| `client.messages.stream(...)` context manager | `client.converse_stream(...)` |
| `stream=True` param | Separate method |
| `with client.messages.stream(...) as stream:` | `response = client.converse_stream(...)` |
| `for text in stream.text_stream:` | Event-based: `contentBlockDelta` → `delta.text` |

## Multimodal Content

| Claude | Nova 2 Lite |
|--------|-------------|
| `{"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":"..."}}` | `{"image":{"format":"jpeg","source":{"bytes": raw_bytes}}}` |
| `{"type":"image","source":{"type":"url","url":"..."}}` | Download → `{"image":{"format":"...","source":{"bytes": raw_bytes}}}` |
| No ordering constraint | Media MUST precede text |
| System prompt: full instructions | System prompt: persona-only for multimodal |

## Response Parsing

| Claude | Nova 2 Lite |
|--------|-------------|
| `response.content[0].text` | `response["output"]["message"]["content"][0]["text"]` |
| `response.content` (list of blocks) | `response["output"]["message"]["content"]` |
| `response.stop_reason` | `response["stopReason"]` |
| `response.usage.input_tokens` | `response["usage"]["inputTokens"]` |
| `response.usage.output_tokens` | `response["usage"]["outputTokens"]` |
| `response.id` | `response["ResponseMetadata"]["RequestId"]` |
| `block.type == "tool_use"` | `"toolUse" in block` |

## Error Handling

| Claude (Anthropic SDK) | Nova 2 Lite (Bedrock) |
|--------|----------------------|
| `anthropic.RateLimitError` | `ThrottlingException` |
| `anthropic.APIError` | `InternalServerError` |
| `anthropic.AuthenticationError` | `AccessDeniedException` |
| `anthropic.BadRequestError` | `ValidationException` |
| `anthropic.APITimeoutError` | `botocore.exceptions.ReadTimeoutError` |

## Features Without Direct Equivalent

| Claude Feature | Nova Alternative |
|----------------|-----------------|
| `cache_control` (prompt caching) | Bedrock prompt caching (different mechanism) |
| Audio input | Pre-transcribe with Amazon Transcribe |
| Computer use | Build with tool use + orchestration |
| Image generation | Amazon Nova Canvas |
| Batch API | Bedrock batch inference |
| `top_k` parameter | Not supported |
