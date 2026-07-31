# Claude → Nova 2 Lite Code Examples

## Example 1: Basic Text Generation (Anthropic Messages API)

### Claude
```python
from anthropic import Anthropic

client = Anthropic(api_key="...")

response = client.messages.create(
    model="claude-3-5-haiku-20241022",
    max_tokens=200,
    system="You are a concise technical writer.",
    messages=[{"role": "user", "content": "Summarize the key benefits of cloud computing."}],
    temperature=0.7,
)
print(response.content[0].text)
```

### Nova 2 Lite
```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a concise technical writer."}],
    messages=[
        {"role": "user", "content": [{"text": "Summarize the key benefits of cloud computing."}]}
    ],
    inferenceConfig={"maxTokens": 200, "temperature": 0.7},
)
print(response["output"]["message"]["content"][0]["text"])
```

---

## Example 2: Tool Use

### Claude
```python
from anthropic import Anthropic

client = Anthropic(api_key="...")

response = client.messages.create(
    model="claude-3-5-haiku-20241022",
    max_tokens=1024,
    tools=[{
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
    }],
    messages=[{"role": "user", "content": "What's the weather in Seattle?"}],
)

for block in response.content:
    if block.type == "tool_use":
        print(f"Call: {block.name}({block.input})")
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
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7, "topP": 0.9},
)

for block in response["output"]["message"]["content"]:
    if "toolUse" in block:
        tool_use = block["toolUse"]
        print(f"Call: {tool_use['name']}({json.dumps(tool_use['input'])})")
```

---

## Example 3: Structured Output (Tool-Forcing)

### Claude
```python
from anthropic import Anthropic

client = Anthropic(api_key="...")

response = client.messages.create(
    model="claude-3-5-haiku-20241022",
    max_tokens=1024,
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

tool_block = next(b for b in response.content if b.type == "tool_use")
print(tool_block.input)
```

### Nova 2 Lite
```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{
        "role": "user",
        "content": [{"text": "Extract from: 'John Smith, 34, lives in Portland'"}],
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

## Example 4: Multimodal (Image)

### Claude
```python
import base64
from anthropic import Anthropic

client = Anthropic(api_key="...")

with open("receipt.png", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

response = client.messages.create(
    model="claude-3-5-haiku-20241022",
    max_tokens=1024,
    system="You are a document extraction assistant.",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
            {"type": "text", "text": "Extract the total amount from this receipt."},
        ],
    }],
)
print(response.content[0].text)
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

## Example 5: Claude-on-Bedrock (Light Path — Model Swap)

### Before (Claude on Bedrock)
```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId="anthropic.claude-3-5-haiku-20241022-v1:0",
    system=[{"text": "You are a helpful assistant."}],
    messages=[
        {"role": "user", "content": [{"text": "Explain microservices vs monoliths."}]}
    ],
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
)
print(response["output"]["message"]["content"][0]["text"])
```

### After (Nova 2 Lite — just swap modelId)
```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a helpful assistant."}],
    messages=[
        {"role": "user", "content": [{"text": "Explain microservices vs monoliths."}]}
    ],
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
)
print(response["output"]["message"]["content"][0]["text"])
```

---

## Example 6: Streaming

### Claude
```python
from anthropic import Anthropic

client = Anthropic(api_key="...")

with client.messages.stream(
    model="claude-3-5-haiku-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a haiku about distributed systems."}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
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

## Example 7: Extended Thinking

### Claude
```python
from anthropic import Anthropic

client = Anthropic(api_key="...")

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=8192,
    thinking={"type": "enabled", "budget_tokens": 4096},
    messages=[{"role": "user", "content": "Prove that the square root of 2 is irrational."}],
)

for block in response.content:
    if block.type == "thinking":
        print("Thinking:", block.thinking[:100], "...")
    elif block.type == "text":
        print("Answer:", block.text)
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
