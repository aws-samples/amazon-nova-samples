# Migration Code Examples

Before/after patterns for migrating Claude to Amazon Nova 2 Lite. The "Before" blocks show the
**Anthropic Messages API**; if the source is **Claude on Bedrock**, the call is already `converse`
and only the `modelId`, reasoning config, and prompt change (see Example 5).

## Example 1: Basic Text Generation

### Claude (Anthropic Messages API)
```python
from anthropic import Anthropic

client = Anthropic(api_key="...")

response = client.messages.create(
    model="claude-3-5-haiku-20241022",
    max_tokens=1024,
    temperature=0.7,
    system="You are a concise technical writer. Keep responses under 100 words.",
    messages=[
        {"role": "user", "content": "Summarize the key benefits of cloud computing."}
    ],
)
print(response.content[0].text)
```

### Nova 2 Lite (Python — boto3)
```python
import boto3
from botocore.config import Config

client = boto3.client("bedrock-runtime", region_name="us-east-1", config=Config(read_timeout=300))

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a concise technical writer. Keep responses under 100 words."}],
    messages=[
        {"role": "user", "content": [{"text": "Summarize the key benefits of cloud computing."}]}
    ],
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
)
print(response["output"]["message"]["content"][0]["text"])
```

Key changes: `anthropic` → `boto3`; API key → IAM; `system` string → `[{"text": ...}]`; `content`
string → `[{"text": ...}]`; `max_tokens`/`temperature` → nested `inferenceConfig` (camelCase);
response `.content[0].text` → `["output"]["message"]["content"][0]["text"]`.

---

## Example 2: Tool Use / Function Calling

### Claude (Anthropic Messages API)
```python
from anthropic import Anthropic

client = Anthropic(api_key="...")

tools = [
    {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
        },
    }
]

response = client.messages.create(
    model="claude-3-5-haiku-20241022",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "What's the weather in Seattle?"}],
)

for block in response.content:
    if block.type == "tool_use":
        print(f"Call: {block.name}({block.input})")
```

### Nova 2 Lite (Python — boto3)
```python
import boto3
import json

client = boto3.client("bedrock-runtime", region_name="us-east-1")

tool_config = {
    "tools": [
        {
            "toolSpec": {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "City name"},
                            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                        },
                        "required": ["location"],
                    }
                },
            }
        }
    ]
}

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "What's the weather in Seattle?"}]}],
    toolConfig=tool_config,
    inferenceConfig={"temperature": 0.7, "topP": 0.9},
)

# Handle tool use, then send the result back
for block in response["output"]["message"]["content"]:
    if "toolUse" in block:
        tool_use = block["toolUse"]
        print(f"Call: {tool_use['name']}({json.dumps(tool_use['input'])})")

        followup = client.converse(
            modelId="us.amazon.nova-2-lite-v1:0",
            messages=[
                {"role": "user", "content": [{"text": "What's the weather in Seattle?"}]},
                {"role": "assistant", "content": response["output"]["message"]["content"]},
                {
                    "role": "user",
                    "content": [
                        {
                            "toolResult": {
                                "toolUseId": tool_use["toolUseId"],
                                "content": [{"text": '{"temperature": 62, "unit": "fahrenheit", "condition": "cloudy"}'}],
                            }
                        }
                    ],
                },
            ],
            toolConfig=tool_config,
            inferenceConfig={"temperature": 0.7, "topP": 0.9},
        )
        print(followup["output"]["message"]["content"][0]["text"])
```

Key changes: `tools=[{name, description, input_schema}]` → `toolConfig={"tools":[{"toolSpec":{...,
"inputSchema":{"json":{...}}}}]}`; Claude `tool_use` block → Nova `toolUse`; `tool_result` →
`toolResult` content block. The JSON Schema body itself is usually a 1:1 lift.

---

## Example 3: Structured Output (JSON)

### Claude (Anthropic Messages API — tool-forcing)
```python
response = client.messages.create(
    model="claude-3-5-haiku-20241022",
    max_tokens=512,
    tools=[{
        "name": "extract_person",
        "description": "Extract structured person data from text",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "city": {"type": "string"},
            },
            "required": ["name", "age", "city"],
        },
    }],
    tool_choice={"type": "tool", "name": "extract_person"},
    messages=[{"role": "user", "content": "Extract from: 'John Smith, 34, lives in Portland'"}],
)
```

### Nova 2 Lite — Simple JSON (inline schema in prompt)
```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

user_prompt = """Extract the person's name, age, and city from: 'John Smith, 34, lives in Portland'

You MUST answer in JSON format only. Write your response following the format below:
```json
{
  "name": "full name as string",
  "age": "integer",
  "city": "city name as string"
}
```
Please generate only the JSON output. DO NOT provide any preamble."""

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": user_prompt}]}],
    inferenceConfig={"temperature": 0},
)
print(response["output"]["message"]["content"][0]["text"])
```

### Nova 2 Lite — Complex JSON (tool-forcing, mirrors Claude's approach)
```python
tool_config = {
    "tools": [
        {
            "toolSpec": {
                "name": "extract_person",
                "description": "Extract structured person data from text",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"},
                            "city": {"type": "string"},
                        },
                        "required": ["name", "age", "city"],
                    }
                },
            }
        }
    ],
    "toolChoice": {"tool": {"name": "extract_person"}},
}

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "Extract from: 'John Smith, 34, lives in Portland'"}]}],
    toolConfig=tool_config,
    inferenceConfig={"temperature": 0},
)
tool_use = response["output"]["message"]["content"][0]["toolUse"]
print(tool_use["input"])  # {"name": "John Smith", "age": 34, "city": "Portland"}
```

Claude's tool-forcing maps almost directly to Nova's `toolChoice={"tool":{"name":...}}`. For
simple schemas (≤10 keys), the inline-prompt variant is lighter and avoids a tool round-trip.

---

## Example 4: Multimodal (Image Analysis)

### Claude (Anthropic Messages API — base64)
```python
import base64

with open("photo.jpg", "rb") as f:
    b64 = base64.standard_b64encode(f.read()).decode()

response = client.messages.create(
    model="claude-3-5-haiku-20241022",
    max_tokens=512,
    system="You are a helpful image analysis assistant.",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": "Describe this image"},
        ],
    }],
)
```

### Nova 2 Lite (Python — boto3)
```python
# Media MUST come before text. System prompt is persona-only — task goes in the user turn.
with open("photo.jpg", "rb") as f:
    image_bytes = f.read()

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a helpful image analysis assistant."}],
    messages=[
        {
            "role": "user",
            "content": [
                {"image": {"format": "jpeg", "source": {"bytes": image_bytes}}},
                {"text": "Describe this image"},
            ],
        }
    ],
    inferenceConfig={"temperature": 0},
)
print(response["output"]["message"]["content"][0]["text"])
```

Key changes: base64 string → raw `bytes`; `{"type":"image","source":{"type":"base64",...}}` →
`{"image":{"format":"jpeg","source":{"bytes":...}}}`; explicit `format` required; media block
placed **before** the text block; any task instructions moved out of `system` into the user turn.

---

## Example 5: Claude on Bedrock → Nova (the light path)

When the customer already calls Claude through Bedrock `converse`, there is no SDK or auth change.

### Before (Claude on Bedrock)
```python
response = client.converse(
    modelId="anthropic.claude-3-5-haiku-20241022-v1:0",
    system=[{"text": "You are a helpful assistant."}],
    messages=[{"role": "user", "content": [{"text": "Explain RAG in two sentences."}]}],
    inferenceConfig={"maxTokens": 512, "temperature": 0.7},
)
```

### After (Nova 2 Lite)
```python
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",   # only the modelId changes here
    system=[{"text": "You are a helpful assistant."}],
    messages=[{"role": "user", "content": [{"text": "Explain RAG in two sentences."}]}],
    inferenceConfig={"maxTokens": 512, "temperature": 0.7},
)
```

The remaining work for this path is the **prompt rewrite** (XML tags → `##Section##`, explicit
task/format/constraints) and, if the Claude call used a `thinking` parameter or
`additionalModelRequestFields`, mapping it to Nova's `reasoningConfig`.

---

## Example 6: Extended Thinking

### Claude (Anthropic Messages API — token budget)
```python
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=4096,
    thinking={"type": "enabled", "budget_tokens": 4000},
    messages=[{"role": "user", "content": "Walk through the proof step by step."}],
)
```

### Nova 2 Lite (categorical effort)
```python
from botocore.config import Config

# High effort can exceed botocore's 60s default — extend the read timeout.
client = boto3.client("bedrock-runtime", region_name="us-east-1", config=Config(read_timeout=3600))

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "Walk through the proof step by step."}]}],
    # At low/medium, inferenceConfig works normally. At "high", OMIT inferenceConfig entirely.
    inferenceConfig={"maxTokens": 2048, "temperature": 0.2},
    additionalModelRequestFields={
        "reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"},  # low / medium / high
    },
)
```

Do NOT copy Claude's `budget_tokens` directly — benchmark low/medium/high and pick the lowest that
meets the quality bar. Extended thinking is **not compatible with streaming** on Nova.
