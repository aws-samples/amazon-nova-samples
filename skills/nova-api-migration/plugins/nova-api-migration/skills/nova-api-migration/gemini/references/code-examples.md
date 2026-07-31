# Gemini → Nova 2 Lite Code Examples

## Example 1: Basic Text Generation

### Gemini (Current SDK — Interactions API)
```python
from google import genai

client = genai.Client()

interaction = client.interactions.create(
    model="gemini-3.5-flash",
    input="Summarize the key benefits of cloud computing.",
    system_instruction="You are a concise technical writer. Keep responses under 100 words.",
)
print(interaction.output_text)
```

### Nova 2 Lite
```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a concise technical writer. Keep responses under 100 words."}],
    messages=[
        {"role": "user", "content": [{"text": "Summarize the key benefits of cloud computing."}]}
    ],
    inferenceConfig={"temperature": 0.7},
)
print(response["output"]["message"]["content"][0]["text"])
```

---

## Example 2: Function Calling / Tool Use

### Gemini
```python
from google import genai
from google.genai import types

client = genai.Client()

tools = types.Tool(function_declarations=[{
    "name": "get_weather",
    "description": "Get current weather for a location",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
        },
        "required": ["location"],
    },
}])

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="What's the weather in Seattle?",
    config=types.GenerateContentConfig(tools=[tools]),
)

for part in response.candidates[0].content.parts:
    if part.function_call:
        print(f"Call: {part.function_call.name}({part.function_call.args})")
```

### Nova 2 Lite
```python
import boto3
import json

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[
        {"role": "user", "content": [{"text": "What's the weather in Seattle?"}]}
    ],
    toolConfig={
        "tools": [{
            "toolSpec": {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "inputSchema": {"json": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"},
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                }},
            }
        }],
        "toolChoice": {"auto": {}},
    },
    inferenceConfig={"temperature": 0.7, "topP": 0.9},
)

for block in response["output"]["message"]["content"]:
    if "toolUse" in block:
        tool_use = block["toolUse"]
        print(f"Call: {tool_use['name']}({json.dumps(tool_use['input'])})")
```

---

## Example 3: Structured Output

### Gemini
```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="Extract the person's name, age, and city from: 'John Smith, 34, lives in Portland'",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "city": {"type": "string"},
            },
            "required": ["name", "age", "city"],
        },
    ),
)
print(response.text)
```

### Nova 2 Lite — Tool-forcing (recommended for reliable schema adherence)
```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{
        "role": "user",
        "content": [{"text": "Extract the person's name, age, and city from: 'John Smith, 34, lives in Portland'"}],
    }],
    toolConfig={
        "tools": [{
            "toolSpec": {
                "name": "extract_person",
                "description": "Extract structured person data from text",
                "inputSchema": {"json": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                        "city": {"type": "string"},
                    },
                    "required": ["name", "age", "city"],
                }},
            }
        }],
        "toolChoice": {"tool": {"name": "extract_person"}},
    },
    inferenceConfig={"temperature": 0},
)

tool_use = response["output"]["message"]["content"][0]["toolUse"]
print(tool_use["input"])  # {"name": "John Smith", "age": 34, "city": "Portland"}
```

---

## Example 4: Multimodal (Image Analysis)

### Gemini
```python
from google import genai
from google.genai import types

client = genai.Client()

with open("receipt.png", "rb") as f:
    image_bytes = f.read()

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=[
        types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
        "Extract the total amount from this receipt.",
    ],
    config=types.GenerateContentConfig(
        system_instruction="You are a document extraction assistant.",
    ),
)
print(response.text)
```

### Nova 2 Lite
```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

with open("receipt.png", "rb") as f:
    image_bytes = f.read()

# Multimodal: system is persona-only; media before text
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a precise document extraction assistant."}],
    messages=[{
        "role": "user",
        "content": [
            {"image": {"format": "png", "source": {"bytes": image_bytes}}},
            {"text": "Extract the total amount from this receipt."},
        ],
    }],
    inferenceConfig={"temperature": 0},
)
print(response["output"]["message"]["content"][0]["text"])
```

---

## Example 5: Streaming

### Gemini
```python
from google import genai

client = genai.Client()

for chunk in client.models.generate_content_stream(
    model="gemini-3.5-flash",
    contents="Write a haiku about distributed systems.",
):
    if chunk.text:
        print(chunk.text, end="", flush=True)
```

### Nova 2 Lite
```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse_stream(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "Write a haiku about distributed systems."}]}],
    inferenceConfig={"temperature": 0.7},
)

for event in response["stream"]:
    if "contentBlockDelta" in event:
        text = event["contentBlockDelta"]["delta"].get("text", "")
        print(text, end="", flush=True)
```

---

## Example 6: Reasoning Mode

### Gemini
```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="Prove that the square root of 2 is irrational.",
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=4096),
    ),
)

for part in response.candidates[0].content.parts:
    if not part.text:
        continue
    if part.thought:
        print("Thinking:", part.text[:100], "...")
    else:
        print("Answer:", part.text)
```

### Nova 2 Lite
```python
import boto3
from botocore.config import Config

client = boto3.client("bedrock-runtime", region_name="us-east-1", config=Config(read_timeout=300))

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[
        {"role": "user", "content": [{"text": "Prove that the square root of 2 is irrational."}]}
    ],
    inferenceConfig={"temperature": 0.7},
    additionalModelRequestFields={
        "reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}
    },
)

for block in response["output"]["message"]["content"]:
    if "reasoningContent" in block:
        print("Reasoning:", block["reasoningContent"]["reasoningText"]["text"][:100], "...")
    elif "text" in block:
        print("Answer:", block["text"])
```

---

## Example 7: Multi-Turn Conversation

### Gemini (Interactions API with `previous_interaction_id`)
```python
from google import genai

client = genai.Client()

turn_1 = client.interactions.create(
    model="gemini-3.5-flash",
    input="My name is Alice and I'm building a Python FastAPI project.",
    system_instruction="You are a helpful coding assistant.",
)

turn_2 = client.interactions.create(
    model="gemini-3.5-flash",
    input="What testing framework do you recommend?",
    previous_interaction_id=turn_1.id,
)
print(turn_2.output_text)
```

### Nova 2 Lite
```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

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

# Append assistant response and next user message
messages.append({"role": "assistant", "content": response_1["output"]["message"]["content"]})
messages.append({"role": "user", "content": [{"text": "What testing framework do you recommend?"}]})

response_2 = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=system,
    messages=messages,
    inferenceConfig={"temperature": 0.7},
)
print(response_2["output"]["message"]["content"][0]["text"])
```
