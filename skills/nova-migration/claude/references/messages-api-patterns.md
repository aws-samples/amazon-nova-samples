# Anthropic Messages API Migration Patterns

Covers the `anthropic` Python SDK (Messages API → `api.anthropic.com`), the `AnthropicBedrock` /
`AnthropicVertex` wrapper clients, and the async client. If the source is plain Claude-on-Bedrock
`converse`, you do not need this file — see `code-examples.md` Example 5.

## SDK Detection

**Anthropic Messages API (direct):**
```python
from anthropic import Anthropic
client = Anthropic(api_key="...")          # or reads ANTHROPIC_API_KEY
response = client.messages.create(model="claude-3-5-haiku-...", ...)
```

**Async client:**
```python
from anthropic import AsyncAnthropic
client = AsyncAnthropic()
response = await client.messages.create(...)
```

**Anthropic SDK over Bedrock / Vertex (wrapper):**
```python
from anthropic import AnthropicBedrock      # or AnthropicVertex
client = AnthropicBedrock()                 # uses AWS creds, but Anthropic request/response shape
response = client.messages.create(model="anthropic.claude-3-5-haiku-...", ...)
```
> `AnthropicBedrock` already runs on AWS infra, but the **request/response shape is still the
> Anthropic Messages format**. Migrating to Nova means dropping the wrapper for `boto3` `converse`
> and reshaping per the tables below — treat it like the direct Messages API for mapping purposes.

---

## Parameter Mapping

| Anthropic Messages API | Nova 2 Lite (boto3) |
|------------------------|---------------------|
| `Anthropic(api_key=...)` | `boto3.client("bedrock-runtime")` (uses AWS creds) |
| `model="claude-3-5-haiku-..."` | `modelId="us.amazon.nova-2-lite-v1:0"` |
| `client.messages.create(...)` | `client.converse(...)` |
| `system="..."` (string) | `system=[{"text": "..."}]` |
| `system=[{"type":"text","text":"..."}]` | `system=[{"text": "..."}]` (drop `type`) |
| `messages=[...]` | `messages=[...]` (reshape content blocks — see below) |
| `max_tokens` (required) | `inferenceConfig.maxTokens` (optional; max 65,536) |
| `temperature` | `inferenceConfig.temperature` |
| `top_p` | `inferenceConfig.topP` |
| `top_k` | Not directly supported — may go in `additionalModelRequestFields` |
| `stop_sequences` | `inferenceConfig.stopSequences` |
| `tools=[...]` | `toolConfig={"tools":[...]}` |
| `tool_choice` | `toolConfig.toolChoice` |
| `thinking={"type":"enabled","budget_tokens":N}` | `additionalModelRequestFields={"reasoningConfig":{...}}` (only when enabled; omit when disabled) |
| `cache_control` blocks | Bedrock prompt caching (separate API surface; not a 1:1 field) |
| `metadata` / `user_id` | No equivalent — drop or track application-side |
| `response.content[0].text` | `response["output"]["message"]["content"][0]["text"]` |
| `response.stop_reason` | `response["stopReason"]` (`end_turn` → `end_turn`, `tool_use` → `tool_use`, `max_tokens` → `max_tokens`) |
| `response.usage.input_tokens / output_tokens` | `response["usage"]["inputTokens"] / ["outputTokens"]` |

---

## Content Format Mapping

### Text-only

**Claude:**
```python
response = client.messages.create(
    model="claude-3-5-haiku-20241022",
    max_tokens=512,
    messages=[{"role": "user", "content": "What is cloud computing?"}],   # string shorthand
)
```

**Nova 2 Lite:**
```python
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "What is cloud computing?"}]}],
    inferenceConfig={"maxTokens": 512},
)
```

### Multi-turn Chat

**Claude:**
```python
messages = [
    {"role": "user", "content": "My name is Alice"},
    {"role": "assistant", "content": "Nice to meet you, Alice."},
    {"role": "user", "content": "What's my name?"},
]
response = client.messages.create(model="claude-3-5-haiku-20241022", max_tokens=256, messages=messages)
```

**Nova 2 Lite:**
```python
messages = [
    {"role": "user", "content": [{"text": "My name is Alice"}]},
    {"role": "assistant", "content": [{"text": "Nice to meet you, Alice."}]},
    {"role": "user", "content": [{"text": "What's my name?"}]},
]
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=messages,
    inferenceConfig={"maxTokens": 256},
)
```
> Role names are identical (`user` / `assistant`) — no rename needed. Only the `content` shape
> changes: bare string → list of typed blocks.

### Multimodal (Image)

**Claude (base64):**
```python
messages = [{
    "role": "user",
    "content": [
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64_str}},
        {"type": "text", "text": "Describe this image"},
    ],
}]
```

**Nova 2 Lite (bytes, media-before-text):**
```python
messages = [{
    "role": "user",
    "content": [
        {"image": {"format": "png", "source": {"bytes": image_bytes}}},
        {"text": "Describe this image"},
    ],
}]
```

### Tool Use Loop

**Claude:**
```python
# 1. Model returns a tool_use block; stop_reason == "tool_use"
tool_block = next(b for b in response.content if b.type == "tool_use")
# 2. Append assistant turn + a user turn carrying the tool_result
messages.append({"role": "assistant", "content": response.content})
messages.append({"role": "user", "content": [{
    "type": "tool_result", "tool_use_id": tool_block.id, "content": result_str,
}]})
# 3. Call again
response = client.messages.create(model=..., max_tokens=1024, tools=tools, messages=messages)
```

**Nova 2 Lite:**
```python
# 1. Model returns a toolUse block; stopReason == "tool_use"
tool_use = next(b["toolUse"] for b in response["output"]["message"]["content"] if "toolUse" in b)
# 2. Append assistant turn + a user turn carrying the toolResult
messages.append({"role": "assistant", "content": response["output"]["message"]["content"]})
messages.append({"role": "user", "content": [{
    "toolResult": {"toolUseId": tool_use["toolUseId"], "content": [{"text": result_str}]},
}]})
# 3. Call again
response = client.converse(modelId=..., toolConfig=tool_config, messages=messages,
                           inferenceConfig={"temperature": 0.7, "topP": 0.9})
```

---

## Streaming

**Claude:**
```python
with client.messages.stream(model="claude-3-5-haiku-20241022", max_tokens=512,
                            messages=[{"role": "user", "content": "Tell me a story."}]) as stream:
    for text in stream.text_stream:
        print(text, end="")
```

**Nova 2 Lite:**
```python
response = client.converse_stream(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "Tell me a story."}]}],
    inferenceConfig={"maxTokens": 512},
)
for event in response["stream"]:
    if "contentBlockDelta" in event:
        print(event["contentBlockDelta"]["delta"].get("text", ""), end="")
```
> Event model differs: Anthropic emits `message_start` / `content_block_delta` / `message_stop`;
> Bedrock emits `contentBlockStart` / `contentBlockDelta` / `contentBlockStop` / `messageStop`.
> Note: Nova extended thinking is **not** compatible with streaming.

---

## Async client

`boto3` is synchronous. For an `AsyncAnthropic` source, either:
- run `converse` in a thread executor: `await loop.run_in_executor(None, lambda: client.converse(...))`, or
- use `aioboto3` (`async with session.client("bedrock-runtime") as client: await client.converse(...)`).

---

## Error handling

**Claude:**
```python
from anthropic import RateLimitError, BadRequestError, APIError

try:
    response = client.messages.create(...)
except RateLimitError:
    ...
except BadRequestError:
    ...
```

**Nova 2 Lite:**
```python
from botocore.exceptions import ClientError, ReadTimeoutError

try:
    response = client.converse(...)
except ClientError as e:
    code = e.response["Error"]["Code"]
    if code == "ThrottlingException":      # was RateLimitError
        ...
    elif code == "ValidationException":    # was BadRequestError
        ...
    elif code == "AccessDeniedException":  # was AuthenticationError / PermissionDeniedError
        ...
except ReadTimeoutError:
    ...                                     # was request-level timeout
```
