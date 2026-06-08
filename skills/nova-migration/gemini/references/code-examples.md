# Migration Code Examples

## Example 1: Basic Text Generation

### Gemini (Python)
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

### Nova 2 Lite (Python — boto3)
```python
import boto3

client = boto3.client("bedrock-runtime")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a concise technical writer. Keep responses under 100 words."}],
    messages=[
        {
            "role": "user",
            "content": [{"text": "Summarize the key benefits of cloud computing."}],
        }
    ],
    inferenceConfig={"temperature": 0.7},
    )

print(response["output"]["message"]["content"][0]["text"])
```

---

## Example 2: Function Calling / Tool Use

### Gemini (Python)
```python
from google import genai
from google.genai import types

client = genai.Client()

get_weather_declaration = {
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
}

tools = types.Tool(function_declarations=[get_weather_declaration])
config = types.GenerateContentConfig(tools=[tools])

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="What's the weather in Seattle?",
    config=config,
)

# Handle function call
for part in response.candidates[0].content.parts:
    if part.function_call:
        print(f"Call: {part.function_call.name}({part.function_call.args})")
```

### Nova 2 Lite (Python — boto3)
```python
import boto3
import json

client = boto3.client("bedrock-runtime")

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
    messages=[
        {"role": "user", "content": [{"text": "What's the weather in Seattle?"}]}
    ],
    toolConfig=tool_config,
    inferenceConfig={"temperature": 0.7, "topP": 0.9},
    )

# Handle tool use
for block in response["output"]["message"]["content"]:
    if "toolUse" in block:
        tool_use = block["toolUse"]
        print(f"Call: {tool_use['name']}({json.dumps(tool_use['input'])})")

        # Send tool result back
        tool_result_response = client.converse(
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
        print(tool_result_response["output"]["message"]["content"][0]["text"])
```

---

## Example 3: Structured Output (JSON)

### Gemini (Python)
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

### Nova 2 Lite — Simple JSON (inline schema in prompt)
```python
import boto3

client = boto3.client("bedrock-runtime")

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

### Nova 2 Lite — Complex JSON (tool-forcing for schema enforcement)
```python
import boto3

client = boto3.client("bedrock-runtime")

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
    messages=[
        {
            "role": "user",
            "content": [{"text": "Extract the person's name, age, and city from: 'John Smith, 34, lives in Portland'"}],
        }
    ],
    toolConfig=tool_config,
    inferenceConfig={"temperature": 0},
    )

# Result is in the toolUse block's input field
tool_use = response["output"]["message"]["content"][0]["toolUse"]
print(tool_use["input"])  # {"name": "John Smith", "age": 34, "city": "Portland"}
```

---

## Example 4: Multimodal (Image Analysis)

### Gemini (Python)
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
        "Extract the total amount, date, and merchant name from this receipt. Return as JSON.",
    ],
    config=types.GenerateContentConfig(
        system_instruction="You are a document extraction assistant.",
    ),
)
print(response.text)
```

### Nova 2 Lite (Python — boto3)
```python
import boto3

client = boto3.client("bedrock-runtime")

with open("receipt.png", "rb") as f:
    image_bytes = f.read()

# CRITICAL: For multimodal, system prompt is persona-only.
# All task instructions go in the user message.
# Media MUST come before text in the content array.

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a precise document extraction assistant."}],
    messages=[
        {
            "role": "user",
            "content": [
                {"image": {"format": "png", "source": {"bytes": image_bytes}}},
                {
                    "text": """Given the image representation of a document, extract information in JSON format according to the given schema.

Follow these guidelines:
- Ensure that every field is populated, provided the document includes the corresponding value. Only use null when the value is absent from the document.

JSON Schema:
{
  "total_amount": "string with currency symbol",
  "date": "YYYY-MM-DD format",
  "merchant_name": "string"
}"""
                },
            ],
        }
    ],
    inferenceConfig={"temperature": 0},
    )
print(response["output"]["message"]["content"][0]["text"])
```

---

## Example 5: Streaming

### Gemini (Python)
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

### Nova 2 Lite (Python — boto3)
```python
import boto3

client = boto3.client("bedrock-runtime")

response = client.converse_stream(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "Write a haiku about distributed systems."}]}],
    inferenceConfig={"temperature": 0.7},
    )

for event in response["stream"]:
    if "contentBlockDelta" in event:
        delta = event["contentBlockDelta"]["delta"]
        if "text" in delta:
            print(delta["text"], end="", flush=True)
```

---

## Example 6: Reasoning Mode

### Gemini (Python)
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

### Nova 2 Lite (Python — boto3)
```python
import boto3

client = boto3.client("bedrock-runtime")

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[
        {"role": "user", "content": [{"text": "Prove that the square root of 2 is irrational."}]}
    ],
    inferenceConfig={"temperature": 0.7},
    additionalModelRequestFields={
        "reasoningConfig": {
            "type": "enabled",
            "maxReasoningEffort": "medium",  # ask user to choose low/medium/high
        }
    },
)

for block in response["output"]["message"]["content"]:
    if "reasoningContent" in block:
        print("Reasoning:", block["reasoningContent"]["reasoningText"]["text"][:100], "...")
    elif "text" in block:
        print("Answer:", block["text"])
```

---

## Example 7: Prompt Structure Migration

### Gemini prompt (XML-style)
```
<context>
You have access to a product catalog with 10,000 items.
</context>

<task>
Classify the user's query into one of: product_search, price_check, availability, other.
</task>

<instructions>
- Only use the categories listed above
- If uncertain, choose "other"
- Respond with just the category name
</instructions>
```

### Nova 2 Lite prompt (##Section## style)
```
##Context Information:##
You have access to a product catalog with 10,000 items.

##Task Summary:##
Classify the user's query into one of: product_search, price_check, availability, other.

##Model Instructions:##
- Only use the categories listed above
- If uncertain, choose "other"
- Respond with just the category name

DO NOT mention anything inside ##Model Instructions## in the response.
```
