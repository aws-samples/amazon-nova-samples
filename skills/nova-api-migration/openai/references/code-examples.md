# OpenAI → Nova 2 Lite Code Examples

## Example 1: Basic Text Generation (Chat Completions)

### OpenAI
```python
from openai import OpenAI

client = OpenAI(api_key="...")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a concise technical writer."},
        {"role": "user", "content": "Summarize the key benefits of cloud computing."},
    ],
    max_tokens=200,
    temperature=0.7,
)
print(response.choices[0].message.content)
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

## Example 2: Function Calling / Tool Use

### OpenAI
```python
from openai import OpenAI

client = OpenAI(api_key="...")

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What's the weather in Seattle?"}],
    tools=[{
        "type": "function",
        "function": {
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
        },
    }],
    tool_choice="auto",
)

tool_call = response.choices[0].message.tool_calls[0]
print(f"Call: {tool_call.function.name}({tool_call.function.arguments})")
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

### OpenAI (JSON Schema mode)
```python
from openai import OpenAI

client = OpenAI(api_key="...")

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Extract name, age, city from: 'John Smith, 34, Portland'"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person_extract",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "city": {"type": "string"},
                },
                "required": ["name", "age", "city"],
            },
        },
    },
)
print(response.choices[0].message.content)
```

### Nova 2 Lite — Tool-forcing
```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{
        "role": "user",
        "content": [{"text": "Extract name, age, city from: 'John Smith, 34, Portland'"}],
    }],
    toolConfig={
        "tools": [{
            "toolSpec": {
                "name": "person_extract",
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
        "toolChoice": {"tool": {"name": "person_extract"}},
    },
    inferenceConfig={"temperature": 0},
)

tool_use = response["output"]["message"]["content"][0]["toolUse"]
print(tool_use["input"])  # {"name": "John Smith", "age": 34, "city": "Portland"}
```

---

## Example 4: Multimodal (Image)

### OpenAI
```python
import base64
from openai import OpenAI

client = OpenAI(api_key="...")

with open("receipt.png", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
            {"type": "text", "text": "Extract the total amount from this receipt."},
        ],
    }],
)
print(response.choices[0].message.content)
```

### Nova 2 Lite
```python
import boto3

client = boto3.client("bedrock-runtime", region_name="us-east-1")

with open("receipt.png", "rb") as f:
    image_bytes = f.read()

# Media MUST precede text; system is persona-only for multimodal
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

### OpenAI
```python
from openai import OpenAI

client = OpenAI(api_key="...")

stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Write a haiku about distributed systems."}],
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
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

## Example 6: Reasoning (GPT-5.x → Nova Extended Thinking)

### OpenAI (Responses API)
```python
from openai import OpenAI

client = OpenAI(api_key="...")

response = client.responses.create(
    model="gpt-5",
    input="Prove that the square root of 2 is irrational.",
    reasoning={"effort": "medium"},
)
print(response.output_text)
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

## Example 7: Tool Result Round-Trip

### OpenAI
```python
from openai import OpenAI
import json

client = OpenAI(api_key="...")

messages = [{"role": "user", "content": "What's the weather in Tokyo?"}]

# First call — model requests tool
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for a city",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        },
    }],
)

tool_call = response.choices[0].message.tool_calls[0]
messages.append(response.choices[0].message)
messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": '{"temp": 22, "condition": "sunny"}'})

# Second call — model uses tool result
final = client.chat.completions.create(model="gpt-4o", messages=messages)
print(final.choices[0].message.content)
```

### Nova 2 Lite
```python
import boto3
import json

client = boto3.client("bedrock-runtime", region_name="us-east-1")

tool_config = {
    "tools": [{
        "toolSpec": {
            "name": "get_weather",
            "description": "Get weather for a city",
            "inputSchema": {"json": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            }},
        }
    }],
    "toolChoice": {"auto": {}},
}

messages = [{"role": "user", "content": [{"text": "What's the weather in Tokyo?"}]}]

# First call — model requests tool
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=messages,
    toolConfig=tool_config,
    inferenceConfig={"temperature": 0.7, "topP": 0.9},
)

# Extract tool use and send result back
assistant_content = response["output"]["message"]["content"]
tool_use = next(b["toolUse"] for b in assistant_content if "toolUse" in b)

messages.append({"role": "assistant", "content": assistant_content})
messages.append({
    "role": "user",
    "content": [{
        "toolResult": {
            "toolUseId": tool_use["toolUseId"],
            "content": [{"text": json.dumps({"temp": 22, "condition": "sunny"})}],
        }
    }],
})

# Second call — model uses tool result
final = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=messages,
    toolConfig=tool_config,
    inferenceConfig={"temperature": 0.7, "topP": 0.9},
)
print(final["output"]["message"]["content"][0]["text"])
```
