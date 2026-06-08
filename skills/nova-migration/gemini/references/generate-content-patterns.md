# Gemini API Migration Patterns

Covers the deprecated `google-generativeai` Python SDK, the current `google-genai` Python SDK's `generateContent` method, and the Interactions API.

## SDK Detection

**Deprecated SDK (`google-generativeai`):**
```python
import google.generativeai as genai
genai.configure(api_key="...")
model = genai.GenerativeModel("gemini-2.0-flash")
response = model.generate_content(...)
```

**Current SDK (`google-genai`) with generateContent:**
```python
from google import genai
client = genai.Client()
response = client.models.generate_content(model="gemini-2.5-flash", ...)
```

**Current SDK (`google-genai`) with Interactions API:**
```python
from google import genai
client = genai.Client()
interaction = client.interactions.create(model="gemini-3.5-flash", ...)
```

---

## Parameter Mapping

### Deprecated SDK (`google-generativeai`)

| Gemini (`google-generativeai`) | Nova 2 Lite (boto3) |
|-------------------------------|---------------------|
| `genai.configure(api_key=...)` | `boto3.client("bedrock-runtime")` (uses AWS creds) |
| `genai.GenerativeModel(model_name)` | `modelId` param in `converse()` |
| `model.generate_content(prompt)` | `client.converse(messages=[...])` |
| `model.generate_content(contents=[...])` | `client.converse(messages=[...])` |
| `model.start_chat(history=[...])` | Pass full message history in `messages` |
| `chat.send_message(msg)` | Append to `messages` and call `converse()` again |
| `response.text` | `response["output"]["message"]["content"][0]["text"]` |
| `response.candidates[0].content.parts` | `response["output"]["message"]["content"]` |

**GenerativeModel constructor params:**

| Gemini | Nova 2 Lite |
|--------|-------------|
| `model_name="gemini-2.0-flash"` | `modelId="us.amazon.nova-2-lite-v1:0"` |
| `system_instruction="..."` | `system=[{"text": "..."}]` |
| `generation_config={...}` | `inferenceConfig={...}` |
| `safety_settings=[...]` | Use `## Guardrails` section in system prompt |
| `tools=[...]` | `toolConfig={"tools": [...]}` |

**GenerationConfig fields:**

| Gemini | Nova 2 Lite |
|--------|-------------|
| `temperature` | `inferenceConfig.temperature` |
| `top_p` | `inferenceConfig.topP` |
| `top_k` | Not supported |
| `max_output_tokens` | `inferenceConfig.maxTokens` |
| `stop_sequences` | `inferenceConfig.stopSequences` |
| `candidate_count` | Not supported (always 1) |
| `response_mime_type="application/json"` | Inline JSON schema in prompt + `temperature=0` |
| `response_schema={...}` | Tool-forcing with schema in `inputSchema` |

**Safety settings:**

| Gemini | Nova 2 Lite |
|--------|-------------|
| `safety_settings=[{"category": "HARM_CATEGORY_...", "threshold": "BLOCK_..."}]` | No equivalent param — use `## Guardrails` section in system prompt to restrict content |

### Current SDK (`google-genai`) with generateContent

| Gemini (`google-genai` generateContent) | Nova 2 Lite (boto3) |
|-----------------------------------------|---------------------|
| `client.models.generate_content(model=..., contents=...)` | `client.converse(modelId=..., messages=...)` |
| `config=types.GenerateContentConfig(...)` | Split across `inferenceConfig`, `system`, `toolConfig`, `additionalModelRequestFields` |
| `config.system_instruction` | `system=[{"text": "..."}]` |
| `config.temperature` | `inferenceConfig={"temperature": ...}` |
| `config.top_p` | `inferenceConfig={"topP": ...}` |
| `config.max_output_tokens` | `inferenceConfig={"maxTokens": ...}` |
| `config.stop_sequences` | `inferenceConfig={"stopSequences": [...]}` |
| `config.response_mime_type` | Inline format instruction in prompt |
| `config.response_schema` | Tool-forcing or inline schema |
| `config.tools` | `toolConfig={"tools": [...]}` |
| `config.tool_config` | `toolConfig={"toolChoice": {...}}` |
| `config.safety_settings` | `## Guardrails` in system prompt |
| `config.thinking_config` | `additionalModelRequestFields={"reasoningConfig": {...}}` (only when enabled; omit entirely when disabled) |
| `response.text` | `response["output"]["message"]["content"][0]["text"]` |
| `response.candidates[0].content.parts` | `response["output"]["message"]["content"]` |
| `response.usage_metadata` | `response["usage"]` |

---

## Content Format Mapping

### Text-only

**Gemini (deprecated SDK):**
```python
response = model.generate_content("What is cloud computing?")
# or
response = model.generate_content(["What is cloud computing?"])
```

**Gemini (current SDK):**
```python
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="What is cloud computing?",
)
```

**Nova 2 Lite:**
```python
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "What is cloud computing?"}]}],
    inferenceConfig={"temperature": 0.7},
    )
```

### Multi-turn Chat

**Gemini (deprecated SDK):**
```python
model = genai.GenerativeModel("gemini-2.0-flash")
chat = model.start_chat(history=[])
response1 = chat.send_message("My name is Alice")
response2 = chat.send_message("What's my name?")
```

**Gemini (current SDK):**
```python
response1 = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[{"role": "user", "parts": [{"text": "My name is Alice"}]}],
)
response2 = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        {"role": "user", "parts": [{"text": "My name is Alice"}]},
        {"role": "model", "parts": [{"text": response1.text}]},
        {"role": "user", "parts": [{"text": "What's my name?"}]},
    ],
)
```

**Nova 2 Lite:**
```python
response1 = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "My name is Alice"}]}],
    inferenceConfig={"temperature": 0.7},
    )

response2 = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[
        {"role": "user", "content": [{"text": "My name is Alice"}]},
        {"role": "assistant", "content": response1["output"]["message"]["content"]},
        {"role": "user", "content": [{"text": "What's my name?"}]},
    ],
    inferenceConfig={"temperature": 0.7},
    )
```

> **Note:** Gemini uses `"role": "model"` for assistant turns. Nova uses `"role": "assistant"`.

### Multimodal (Image)

**Gemini (deprecated SDK):**
```python
import PIL.Image

img = PIL.Image.open("photo.png")
response = model.generate_content([img, "Describe this image"])
# or with raw bytes:
response = model.generate_content([
    {"mime_type": "image/png", "data": image_bytes},
    "Describe this image"
])
```

**Gemini (current SDK):**
```python
from google.genai import types

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        types.Part.from_image(image_bytes, mime_type="image/png"),
        "Describe this image",
    ],
)
```

**Nova 2 Lite:**
```python
# Media MUST come before text. System prompt is persona-only.
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a helpful image analysis assistant."}],
    messages=[
        {
            "role": "user",
            "content": [
                {"image": {"format": "png", "source": {"bytes": image_bytes}}},
                {"text": "Describe this image"},
            ],
        }
    ],
    inferenceConfig={"temperature": 0},
    )
```

### Function Calling

**Gemini (deprecated SDK):**
```python
import google.generativeai as genai

def get_weather(location: str, unit: str = "celsius"):
    """Get weather for a location."""
    return {"temp": 22, "unit": unit}

model = genai.GenerativeModel(
    "gemini-2.0-flash",
    tools=[get_weather],  # can pass Python functions directly
)
response = model.generate_content("Weather in Tokyo?")

# Or with manual tool definition:
tools = [{
    "function_declarations": [{
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
        },
    }]
}]
model = genai.GenerativeModel("gemini-2.0-flash", tools=tools)
```

**Gemini (current SDK):**
```python
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Weather in Tokyo?",
    config=types.GenerateContentConfig(
        tools=[{
            "function_declarations": [{
                "name": "get_weather",
                "description": "Get weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            }]
        }],
        tool_config={"function_calling_config": {"mode": "AUTO"}},
    ),
)
```

**Nova 2 Lite:**
```python
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "Weather in Tokyo?"}]}],
    toolConfig={
        "tools": [{
            "toolSpec": {
                "name": "get_weather",
                "description": "Get weather for a location",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"},
                            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                        },
                        "required": ["location"],
                    }
                },
            }
        }],
        "toolChoice": {"auto": {}},
    },
    inferenceConfig={"temperature": 0.7, "topP": 0.9},
    )
```

> **Note:** Gemini's deprecated SDK allows passing Python functions directly as tools (auto-extracts schema from type hints). Nova requires explicit tool schema definitions.

### Structured Output (JSON mode)

**Gemini (deprecated SDK):**
```python
model = genai.GenerativeModel(
    "gemini-2.0-flash",
    generation_config=genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        },
    ),
)
response = model.generate_content("Extract name and age from: 'Bob is 25'")
```

**Gemini (current SDK):**
```python
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Extract name and age from: 'Bob is 25'",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name", "age"],
        },
    ),
)
```

**Nova 2 Lite (simple — inline prompt schema):**
```python
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{
        "role": "user",
        "content": [{"text": """Extract name and age from: 'Bob is 25'

You MUST answer in JSON format only. Write your response following the format below:
```json
{
  "name": "full name as string",
  "age": "integer"
}
```
Please generate only the JSON output. DO NOT provide any preamble."""}],
    }],
    inferenceConfig={"temperature": 0},
    )
```

**Nova 2 Lite (complex — tool-forcing):**
```python
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{
        "role": "user",
        "content": [{"text": "Extract name and age from: 'Bob is 25'"}],
    }],
    toolConfig={
        "tools": [{
            "toolSpec": {
                "name": "extract_info",
                "description": "Extract structured data from text",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"},
                        },
                        "required": ["name", "age"],
                    }
                },
            }
        }],
        "toolChoice": {"tool": {"name": "extract_info"}},
    },
    inferenceConfig={"temperature": 0},
    )
# Result in: response["output"]["message"]["content"][0]["toolUse"]["input"]
```

### Streaming

**Gemini (deprecated SDK):**
```python
response = model.generate_content("Write a story", stream=True)
for chunk in response:
    print(chunk.text, end="")
```

**Gemini (current SDK):**
```python
response = client.models.generate_content_stream(
    model="gemini-2.5-flash",
    contents="Write a story",
)
for chunk in response:
    print(chunk.text, end="")
```

**Nova 2 Lite:**
```python
response = client.converse_stream(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "Write a story"}]}],
    inferenceConfig={"temperature": 0.7},
    )
for event in response["stream"]:
    if "contentBlockDelta" in event:
        text = event["contentBlockDelta"]["delta"].get("text", "")
        print(text, end="")
```

---

## Deprecated SDK Gotchas

| Pattern | Migration Notes |
|---------|----------------|
| `genai.configure(api_key=...)` | Remove entirely — boto3 uses AWS credential chain |
| `GenerativeModel(tools=[python_function])` | Must write explicit tool schema — no auto-extraction |
| `model.count_tokens(...)` | Not available in converse API — estimate or use separate token counting |
| `chat = model.start_chat()` | No chat object — maintain message list yourself |
| `response.prompt_feedback` | Not available — use CloudWatch metrics |
| `response.candidates[0].finish_reason` | `response["stopReason"]` (values: `end_turn`, `tool_use`, `max_tokens`, `stop_sequence`) |
| `PIL.Image` as input | Read raw bytes and pass as `{"image": {"format": "...", "source": {"bytes": ...}}}` |
| `genai.upload_file(...)` | Not available — pass bytes inline or use S3 URI for large files |

---

## Interactions API Migration Patterns

The Interactions API (`client.interactions.create`) is the newest Gemini API pattern (google-genai >= 2.0). It provides a simplified interface that wraps `generateContent` with stateful multi-turn via `previous_interaction_id`.

### Parameter Mapping

| Gemini Interactions API | Nova 2 Lite (boto3 converse) |
|------------------------|------------------------------|
| `client.interactions.create(...)` | `client.converse(...)` |
| `model="gemini-3.5-flash"` | `modelId="us.amazon.nova-2-lite-v1:0"` |
| `input="..."` (string) | `messages=[{"role": "user", "content": [{"text": "..."}]}]` |
| `system_instruction="..."` | `system=[{"text": "..."}]` |
| `config=types.GenerateContentConfig(...)` | Split across `inferenceConfig`, `toolConfig`, `additionalModelRequestFields` |
| `config.temperature` | `inferenceConfig={"temperature": ...}` |
| `config.max_output_tokens` | `inferenceConfig={"maxTokens": ...}` |
| `config.tools` | `toolConfig={"tools": [...]}` |
| `config.thinking_config` | `additionalModelRequestFields={"reasoningConfig": {...}}` (only when enabled; omit entirely when disabled) |
| `previous_interaction_id=interaction.id` | Pass full `messages` array with conversation history |
| `interaction.output_text` | `response["output"]["message"]["content"][0]["text"]` |

### Basic Text

**Gemini (Interactions API):**
```python
from google import genai

client = genai.Client()

interaction = client.interactions.create(
    model="gemini-3.5-flash",
    input="Explain microservices vs monoliths.",
    system_instruction="You are a senior architect. Be concise.",
)
print(interaction.output_text)
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

### Multi-Turn with `previous_interaction_id`

Gemini's Interactions API uses `previous_interaction_id` for stateful multi-turn — the server retains context. Nova has no server-side state; you must pass the full message history.

**Gemini (Interactions API):**
```python
from google import genai

client = genai.Client()

turn_1 = client.interactions.create(
    model="gemini-3.5-flash",
    input="My name is Alice and I'm building a Python FastAPI project.",
    system_instruction="You are a helpful coding assistant.",
)
print("Turn 1:", turn_1.outputs[-1].text)

turn_2 = client.interactions.create(
    model="gemini-3.5-flash",
    input="What testing framework do you recommend for my project?",
    previous_interaction_id=turn_1.id,
)
print("Turn 2:", turn_2.outputs[-1].text)
```

**Nova 2 Lite:**
```python
import boto3

client = boto3.client("bedrock-runtime")

system = [{"text": "You are a helpful coding assistant."}]
messages = [
    {"role": "user", "content": [{"text": "My name is Alice and I'm building a Python FastAPI project."}]}
]

response_1 = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=system,
    messages=messages,
    inferenceConfig={"temperature": 0.7},
    )
print("Turn 1:", response_1["output"]["message"]["content"][0]["text"])

# Append assistant response and next user message to history
messages.append({"role": "assistant", "content": response_1["output"]["message"]["content"]})
messages.append({"role": "user", "content": [{"text": "What testing framework do you recommend for my project?"}]})

response_2 = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=system,
    messages=messages,
    inferenceConfig={"temperature": 0.7},
    )
print("Turn 2:", response_2["output"]["message"]["content"][0]["text"])
```

### Interactions API with Tools

**Gemini (Interactions API):**
```python
from google import genai
from google.genai import types

client = genai.Client()

get_order_status_declaration = {
    "name": "get_order_status",
    "description": "Look up the status of a customer order",
    "parameters": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "The order ID"},
        },
        "required": ["order_id"],
    },
}

tools = types.Tool(function_declarations=[get_order_status_declaration])

interaction = client.interactions.create(
    model="gemini-3.5-flash",
    input="What's the status of order ORD-12345?",
    system_instruction="You are a customer support agent. Use tools to look up information.",
    config=types.GenerateContentConfig(tools=[tools]),
)

for output in interaction.outputs:
    if output.function_call:
        print(f"Tool call: {output.function_call.name}({output.function_call.args})")
    elif output.text:
        print(output.text)
```

**Nova 2 Lite:**
```python
import boto3
import json

client = boto3.client("bedrock-runtime")

tool_config = {
    "tools": [
        {
            "toolSpec": {
                "name": "get_order_status",
                "description": "Look up the status of a customer order",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "order_id": {"type": "string", "description": "The order ID"},
                        },
                        "required": ["order_id"],
                    }
                },
            }
        }
    ],
}

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a customer support agent. Use the 'get_order_status' tool to look up information."}],
    messages=[
        {"role": "user", "content": [{"text": "What's the status of order ORD-12345?"}]}
    ],
    toolConfig=tool_config,
    inferenceConfig={"temperature": 0.7, "topP": 0.9},
    )

for block in response["output"]["message"]["content"]:
    if "toolUse" in block:
        tool_use = block["toolUse"]
        print(f"Tool call: {tool_use['name']}({json.dumps(tool_use['input'])})")
    elif "text" in block:
        print(block["text"])
```

### Interactions API with Thinking/Reasoning

**Gemini (Interactions API):**
```python
from google import genai
from google.genai import types

client = genai.Client()

interaction = client.interactions.create(
    model="gemini-3.5-flash",
    input="Prove that there are infinitely many prime numbers.",
    system_instruction="You are a mathematics professor.",
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=8192),
    ),
)
print(interaction.output_text)
```

**Nova 2 Lite:**
```python
import boto3

client = boto3.client("bedrock-runtime")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a mathematics professor."}],
    messages=[
        {"role": "user", "content": [{"text": "Prove that there are infinitely many prime numbers."}]}
    ],
    inferenceConfig={"temperature": 0.7},
    additionalModelRequestFields={
        "reasoningConfig": {
            "type": "enabled",
            "maxReasoningEffort": "medium",  # ask user to choose low/medium/high
        }
    },
)
print(response["output"]["message"]["content"][0]["text"])
```

### Interactions API Gotchas

| Pattern | Migration Notes |
|---------|----------------|
| `previous_interaction_id=interaction.id` | No server-side state — maintain and pass full `messages` array |
| `interaction.output_text` | `response["output"]["message"]["content"][0]["text"]` |
| `interaction.steps` (list of ThoughtStep/ModelOutputStep) | `response["output"]["message"]["content"]` (list of content blocks) |
| `step.content[].function_call` (on ModelOutputStep) | `block["toolUse"]` in content blocks |
| `store=True` (persist interaction) | Not available — manage state externally (DB, cache, etc.) |
| `interaction.id` | No equivalent — track conversation state in your application |
