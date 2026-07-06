# OpenAI API Migration Patterns

Covers the three OpenAI API styles you may encounter: the **Chat Completions API** (`client.chat.completions.create`), the newer **Responses API** (`client.responses.create`), and the stateful **Assistants API** (`client.beta.assistants.*` / threads).

## API Style Detection

**Chat Completions API (most common):**
```python
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(model="gpt-4o", messages=[...])
```

**Responses API (newer):**
```python
from openai import OpenAI
client = OpenAI()
response = client.responses.create(
    model="gpt-4o",
    instructions="You are a helpful assistant.",   # system prompt
    input="Explain microservices.",                 # user input
)
```

**Assistants API (stateful, built-in tools):**
```python
from openai import OpenAI
client = OpenAI()
assistant = client.beta.assistants.create(model="gpt-4o", instructions="...", tools=[...])
thread = client.beta.threads.create()
client.beta.threads.messages.create(thread_id=thread.id, role="user", content="...")
run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
```

All three map to a single Nova `client.converse(...)` call. Nova has no server-side state, so any stateful pattern becomes "pass the full message history each call."

---

## Chat Completions API

### Parameter Mapping

| OpenAI (Chat Completions) | Nova 2 Lite (boto3) |
|---------------------------|---------------------|
| `client.chat.completions.create(model=..., messages=...)` | `client.converse(modelId=..., messages=...)` |
| `{"role": "system", "content": "..."}` (in messages) | `system=[{"text": "..."}]` (separate param) |
| `{"role": "user", "content": "text"}` | `{"role": "user", "content": [{"text": "text"}]}` |
| `temperature` | `inferenceConfig={"temperature": ...}` |
| `top_p` | `inferenceConfig={"topP": ...}` |
| `max_tokens` / `max_completion_tokens` | `inferenceConfig={"maxTokens": ...}` |
| `stop` | `inferenceConfig={"stopSequences": [...]}` |
| `tools` | `toolConfig={"tools": [...]}` |
| `tool_choice` | `toolConfig={"toolChoice": {...}}` |
| `response_format` | Inline schema in prompt or tool-forcing |
| `reasoning_effort` (GPT-5.x) | `additionalModelRequestFields={"reasoningConfig": {...}}` (only when enabled) |
| `stream=True` | `client.converse_stream(...)` |
| `response.choices[0].message.content` | `response["output"]["message"]["content"][0]["text"]` |
| `response.choices[0].finish_reason` | `response["stopReason"]` (`end_turn`, `tool_use`, `max_tokens`, `stop_sequence`) |
| `response.usage` | `response["usage"]` |

### Multi-turn Chat

OpenAI Chat Completions is already stateless — you pass the full `messages` array each call, just like Nova. The migration is mostly mechanical: extract the system message, wrap content in typed blocks.

**OpenAI:**
```python
messages = [
    {"role": "system", "content": "You are a helpful coding assistant."},
    {"role": "user", "content": "My name is Alice, building a FastAPI project."},
]
r1 = client.chat.completions.create(model="gpt-4o", messages=messages)

messages.append({"role": "assistant", "content": r1.choices[0].message.content})
messages.append({"role": "user", "content": "What testing framework do you recommend?"})
r2 = client.chat.completions.create(model="gpt-4o", messages=messages)
```

**Nova 2 Lite:**
```python
import boto3
client = boto3.client("bedrock-runtime")

system = [{"text": "You are a helpful coding assistant."}]
messages = [
    {"role": "user", "content": [{"text": "My name is Alice, building a FastAPI project."}]}
]

r1 = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=system,
    messages=messages,
    inferenceConfig={"temperature": 0.7},
)

# Append the assistant's content blocks directly, then the next user turn
messages.append({"role": "assistant", "content": r1["output"]["message"]["content"]})
messages.append({"role": "user", "content": [{"text": "What testing framework do you recommend?"}]})

r2 = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=system,
    messages=messages,
    inferenceConfig={"temperature": 0.7},
)
```

---

## Responses API

The Responses API splits the prompt into `instructions` (system) and `input` (user), and supports stateful chaining via `previous_response_id`.

### Parameter Mapping

| OpenAI (Responses API) | Nova 2 Lite (boto3) |
|------------------------|---------------------|
| `client.responses.create(...)` | `client.converse(...)` |
| `model="gpt-4o"` | `modelId="us.amazon.nova-2-lite-v1:0"` |
| `instructions="..."` | `system=[{"text": "..."}]` |
| `input="..."` (string) | `messages=[{"role": "user", "content": [{"text": "..."}]}]` |
| `input=[{"role": ..., "content": ...}]` (list) | `messages=[...]` with typed content blocks |
| `temperature` / `top_p` / `max_output_tokens` | `inferenceConfig={"temperature", "topP", "maxTokens"}` |
| `tools=[...]` | `toolConfig={"tools": [...]}` |
| `reasoning={"effort": "high"}` | `additionalModelRequestFields={"reasoningConfig": {...}}` |
| `previous_response_id=resp.id` | Pass full `messages` array with conversation history |
| `store=True` (persist server-side) | Not available — manage state externally |
| `response.output_text` | `response["output"]["message"]["content"][0]["text"]` |

### Basic Text

**OpenAI (Responses API):**
```python
from openai import OpenAI
client = OpenAI()

resp = client.responses.create(
    model="gpt-4o",
    instructions="You are a senior architect. Be concise.",
    input="Explain microservices vs monoliths.",
)
print(resp.output_text)
```

**Nova 2 Lite:**
```python
import boto3
client = boto3.client("bedrock-runtime")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a senior architect. Be concise."}],
    messages=[
        {"role": "user", "content": [{"text": "Explain microservices vs monoliths."}]}
    ],
    inferenceConfig={"temperature": 0.7},
)
print(response["output"]["message"]["content"][0]["text"])
```

### Multi-turn with `previous_response_id`

The Responses API can retain context server-side via `previous_response_id`. Nova has no server-side state — maintain and pass the full message history.

**OpenAI (Responses API):**
```python
turn_1 = client.responses.create(
    model="gpt-4o",
    instructions="You are a helpful coding assistant.",
    input="My name is Alice, building a FastAPI project.",
)
turn_2 = client.responses.create(
    model="gpt-4o",
    previous_response_id=turn_1.id,
    input="What testing framework do you recommend?",
)
print(turn_2.output_text)
```

**Nova 2 Lite:** identical to the Chat Completions multi-turn pattern above — accumulate `messages` and pass them each call.

---

## Assistants API

The Assistants API is stateful (threads persist messages) and ships built-in tools (code interpreter, file search). Nova replaces the *state* with client-side history and replaces the *built-in tools* with Nova's own.

### Concept Mapping

| OpenAI (Assistants API) | Nova 2 Lite |
|-------------------------|-------------|
| `assistants.create(instructions=...)` | `system=[{"text": "..."}]` on each `converse` call |
| `threads.create()` + `threads.messages.create(...)` | Maintain a `messages` list in your application |
| `threads.runs.create(...)` + polling | A single synchronous `client.converse(...)` call |
| `previous` thread state | Pass the full `messages` array each call |
| Tool: `{"type": "code_interpreter"}` | Built-in `nova_code_interpreter` tool (see below) |
| Tool: `{"type": "file_search"}` (vector stores) | Amazon Bedrock Knowledge Bases |
| Tool: `{"type": "function", ...}` | `toolConfig={"tools": [{"toolSpec": ...}]}` |
| `run.status` polling loop | No polling — `converse` returns synchronously |

### Built-in Tools Migration

Where OpenAI requires the Assistants API to access code execution or retrieval, Nova 2 Lite exposes equivalents through the same `toolConfig` parameter on the standard `converse` call — no separate API surface.

**Code interpreter** (`nova_code_interpreter`):
- Executes Python in an isolated sandbox for precise computation.
- Available in US East (N. Virginia), US West (Oregon), and Asia Pacific (Tokyo). Use Global CRIS (`global.amazon.nova-2-lite-v1:0`) to route to a supported Region.
- Requires `bedrock:InvokeTool` IAM permission (not included in the default Bedrock role).

**Web grounding** (`nova_grounding`):
- Provides real-time web information with citations.
- Available in US AWS Regions only.
- Requires `bedrock:InvokeTool` IAM permission for the `amazon.nova_grounding` resource. Incurs additional cost beyond standard inference.

The model decides when to invoke these based on prompt context. For the exact `toolConfig` payloads and response parsing, see the [built-in tools section of the companion blog post](https://aws.amazon.com/blogs/machine-learning/migrate-from-amazon-nova-1-to-amazon-nova-2-on-amazon-bedrock/) and the [Amazon Nova 2 User Guide — using tools](https://docs.aws.amazon.com/nova/latest/nova2-userguide/using-tools.html).

**File search / retrieval:** there is no inline equivalent. Replace OpenAI vector stores with Amazon Bedrock Knowledge Bases and retrieve context before the `converse` call, passing it under a `##Reference##` section.

### Assistants API Gotchas

| Pattern | Migration Notes |
|---------|----------------|
| `threads.runs.create(...)` + status polling | No async run lifecycle — `converse` is synchronous |
| Thread persistence | No server-side threads — store the `messages` list yourself (DB, cache) |
| `code_interpreter` tool | `nova_code_interpreter` built-in tool; add `InvokeTool` IAM permission |
| `file_search` tool | Amazon Bedrock Knowledge Bases; retrieve then inject as `##Reference##` |
| Assistant-level `instructions` | Re-send `system=[{"text": ...}]` on every call |
| Uploaded files (`purpose="assistants"`) | Pass bytes inline (image/document blocks) or stage in S3 |

---

## Common Gotchas (All API Styles)

| Pattern | Migration Notes |
|---------|----------------|
| `OpenAI(api_key=...)` | Remove — boto3 uses the AWS credential chain (IAM role / profile / env) |
| Flat string `content` | Wrap in typed blocks: `[{"text": "..."}]` |
| `{"role": "system", ...}` in messages | Extract to the `system=[...]` parameter |
| Image as URL / base64 data URI | Read raw bytes → `{"image": {"format": "...", "source": {"bytes": ...}}}` |
| `n` > 1 | Not supported — make multiple calls |
| `seed` | Not supported |
| `finish_reason` | `response["stopReason"]` (`end_turn`, `tool_use`, `max_tokens`, `stop_sequence`) |
| Token counting helper | No `count_tokens` on converse — estimate, or count before sending |
| `response_format` (JSON) | Inline schema in prompt (simple) or tool-forcing (complex) |
