# OpenAI → Nova 2 Lite API Feature Mapping

## SDK & Client Initialization

| OpenAI | Nova 2 Lite (Bedrock) |
|--------|----------------------|
| `from openai import OpenAI` | `import boto3` |
| `client = OpenAI(api_key="...")` | `client = boto3.client("bedrock-runtime", region_name="us-east-1")` |
| `OPENAI_API_KEY` env var | AWS credentials (IAM role, profile, or env vars) |
| `client.chat.completions.create(...)` | `client.converse(...)` |
| `client.responses.create(...)` | `client.converse(...)` |
| `client.beta.assistants.create(...)` | No direct equivalent — use `converse` with tool use |

## Model IDs

| OpenAI Model | Nova Model ID |
|--------------|---------------------|
| `gpt-4o` / `gpt-4o-mini` | `us.amazon.nova-2-lite-v1:0` |
| `gpt-4.1` / `gpt-4.1-mini` | `us.amazon.nova-2-lite-v1:0` |
| `gpt-4` / `gpt-3.5-turbo` | `us.amazon.nova-2-lite-v1:0` |
| `gpt-5` / `gpt-5.2` / `o3` / `o1` | `us.amazon.nova-2-lite-v1:0` — **ask user to confirm** |

## System Prompt

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `{"role": "system", "content": "..."}` in messages array | `system=[{"text": "..."}]` (top-level param, NOT in messages) |
| Responses API: `instructions="..."` | `system=[{"text": "..."}]` |
| Responses API on Bedrock: `{"role": "developer", "content": "..."}` | `system=[{"text": "..."}]` |
| System message persists in the array | Re-specify `system` each call |
| Full instructions for all modalities | **Multimodal**: persona-only in system; task instructions in user message |

## Messages / Content

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `messages=[{"role": "user", "content": "Hello"}]` (string) | `messages=[{"role": "user", "content": [{"text": "Hello"}]}]` (typed blocks) |
| `{"role": "system", ...}` | Extract to `system` param; remove from messages |
| `{"role": "assistant", ...}` | `{"role": "assistant", ...}` (same) |
| `{"role": "tool", "tool_call_id": ..., "content": ...}` | `{"role": "user", "content": [{"toolResult": {...}}]}` |
| Multimodal: `{"type": "image_url", "image_url": {"url": ...}}` | `{"image": {"format": "jpeg", "source": {"bytes": ...}}}` |
| Media ordering flexible | Media MUST come before text in content array |

## Inference Parameters

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `max_tokens` (top-level) | `inferenceConfig={"maxTokens": ...}` |
| `temperature` (top-level) | `inferenceConfig={"temperature": ...}` |
| `top_p` (top-level) | `inferenceConfig={"topP": ...}` |
| `stop` (top-level) | `inferenceConfig={"stopSequences": [...]}` |
| `n` (multiple completions) | Not supported (always 1) |
| `frequency_penalty` / `presence_penalty` | Not directly supported |
| `logprobs` | Not supported |
| `seed` | Not supported |

## Function Calling / Tool Use

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `tools=[{"type": "function", "function": {...}}]` | `toolConfig={"tools": [{"toolSpec": {...}}]}` |
| `function.name` | `toolSpec.name` |
| `function.description` | `toolSpec.description` |
| `function.parameters` (JSON Schema) | `toolSpec.inputSchema.json` (JSON Schema — re-wrap) |
| `tool_choice="auto"` | `toolChoice={"auto": {}}` |
| `tool_choice="required"` | `toolChoice={"any": {}}` |
| `tool_choice="none"` | Remove `toolConfig` entirely |
| `tool_choice={"type":"function","function":{"name":"X"}}` | `toolChoice={"tool": {"name": "X"}}` |
| Response: `message.tool_calls[].function` | Response: `toolUse` content block |
| `tool_calls[].id` | `toolUse.toolUseId` |
| `tool_calls[].function.name` | `toolUse.name` |
| `tool_calls[].function.arguments` (JSON string) | `toolUse.input` (parsed dict) |
| Send back: `{"role": "tool", "tool_call_id": ..., "content": ...}` | `{"role": "user", "content": [{"toolResult": {"toolUseId": ..., "content": [{"text": ...}]}}]}` |

## Structured Output

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `response_format={"type": "json_object"}` | Inline JSON instruction in prompt + `temperature=0` |
| `response_format={"type": "json_schema", "json_schema": {...}}` | Tool-forcing with schema in `inputSchema` |
| Pydantic model as `response_format` | Tool-forcing with equivalent JSON Schema |
| Schema enforced natively | Schema enforced via `toolChoice={"tool":{"name":"..."}}` |

## Reasoning

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `reasoning_effort="low"/"medium"/"high"` (GPT-5.x) | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "..."}}` |
| `reasoning={"effort": "medium"}` (Responses API) | Same as above |
| `o1`/`o3` (always-reason models) | Enable reasoning; ask user for effort level |
| Default: disabled for GPT-4x | Default: disabled — omit `additionalModelRequestFields` |

## Streaming

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `stream=True` param on same method | Separate method: `client.converse_stream(...)` |
| `for chunk in response: chunk.choices[0].delta.content` | `for event in response["stream"]: event["contentBlockDelta"]["delta"]["text"]` |
| Server-sent events | Event stream with typed event objects |

## Multimodal Content

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `{"type": "image_url", "image_url": {"url": "https://..."}}` | Download → `{"image": {"format": "jpeg", "source": {"bytes": ...}}}` |
| `{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}` | Decode → `{"image": {"format": "png", "source": {"bytes": ...}}}` |
| Images via URL or base64 | Images as raw bytes or S3 URI |
| Video not supported via Chat Completions | Video via `{"video": {"format": "mp4", "source": {"bytes": ...}}}` |
| No ordering constraint | Media MUST precede text |

## Response Parsing

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `response.choices[0].message.content` | `response["output"]["message"]["content"][0]["text"]` |
| `response.choices[0].message.tool_calls` | `response["output"]["message"]["content"]` (filter for `toolUse`) |
| `response.choices[0].finish_reason` | `response["stopReason"]` |
| `response.usage.prompt_tokens` | `response["usage"]["inputTokens"]` |
| `response.usage.completion_tokens` | `response["usage"]["outputTokens"]` |
| `response.id` | `response["ResponseMetadata"]["RequestId"]` |

## Error Handling

| OpenAI | Nova 2 Lite (Bedrock) |
|--------|----------------------|
| `openai.RateLimitError` | `botocore.exceptions.ClientError` (ThrottlingException) |
| `openai.APIError` | `botocore.exceptions.ClientError` (InternalServerError) |
| `openai.AuthenticationError` | `botocore.exceptions.ClientError` (AccessDeniedException) |
| `openai.BadRequestError` | `botocore.exceptions.ClientError` (ValidationException) |
| `openai.APITimeoutError` | `botocore.exceptions.ReadTimeoutError` |

## Features Without Direct Equivalent

| OpenAI Feature | Nova Alternative |
|----------------|-----------------|
| Assistants API / Threads | Manage conversation history externally |
| Code Interpreter (Assistants) | `amazon.nova_code_interpreter` built-in tool |
| File Search / Retrieval (Assistants) | Amazon Bedrock Knowledge Bases |
| Web Search built-in tool | `amazon.nova_grounding` built-in tool |
| Image generation (DALL-E) | Amazon Nova Canvas (separate model) |
| TTS / Whisper | Amazon Polly / Amazon Transcribe |
| Realtime API (voice) | Amazon Nova Sonic |
| Fine-tuned models | Re-run customization on Bedrock |
| Batch API | Bedrock batch inference |
| `n` (multiple completions) | Not supported — call multiple times |
| `logprobs` | Not supported |
