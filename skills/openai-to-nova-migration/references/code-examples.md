# Migration Code Examples

All examples migrate OpenAI Python code to Amazon Nova 2 Lite on Amazon Bedrock (`boto3` Bedrock Runtime `converse` API).

## Example 1: Basic Text Generation

### OpenAI (Python)
```python
from openai import OpenAI

client = OpenAI(api_key="sk-...")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a concise technical writer. Keep responses under 100 words."},
        {"role": "user", "content": "Summarize the key benefits of cloud computing."},
    ],
    temperature=0.7,
    max_tokens=512,
)
print(response.choices[0].message.content)
```

### Nova 2 Lite (Python — boto3)
```python
import boto3

client = boto3.client("bedrock-runtime")

# System message extracted to the `system` parameter.
# User content wrapped in a typed block. Params nested in inferenceConfig.
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a concise technical writer. Keep responses under 100 words."}],
    messages=[
        {"role": "user", "content": [{"text": "Summarize the key benefits of cloud computing."}]}
    ],
    inferenceConfig={"temperature": 0.7, "maxTokens": 512},
)

print(response["output"]["message"]["content"][0]["text"])
```

---

## Example 2: Function Calling / Tool Use

### OpenAI (Python)
```python
from openai import OpenAI
import json

client = OpenAI()

tools = [
    {
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
    }
]

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What's the weather in Seattle?"}],
    tools=tools,
    tool_choice="auto",
)

for call in response.choices[0].message.tool_calls or []:
    print(f"Call: {call.function.name}({call.function.arguments})")
```

### Nova 2 Lite (Python — boto3)
```python
import boto3
import json

client = boto3.client("bedrock-runtime")

# OpenAI's function.parameters (JSON Schema) re-wrapped in toolSpec.inputSchema.json
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

        # Send tool result back — note the toolResult goes in a user-role message
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

### OpenAI (Python — Structured Outputs)
```python
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "Extract the person's name, age, and city from: 'John Smith, 34, lives in Portland'"}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person",
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

### OpenAI (Python)
```python
from openai import OpenAI
import base64

client = OpenAI()

with open("receipt.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a document extraction assistant."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract the total amount, date, and merchant name from this receipt. Return as JSON."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        },
    ],
)
print(response.choices[0].message.content)
```

### Nova 2 Lite (Python — boto3)
```python
import boto3

client = boto3.client("bedrock-runtime")

with open("receipt.png", "rb") as f:
    image_bytes = f.read()

# CRITICAL multimodal rules:
#   1. System prompt is persona-only — all task instructions move to the user message.
#   2. Media MUST come before text in the content array.
#   3. Image is raw bytes, not a base64 data URI.

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

### OpenAI (Python)
```python
from openai import OpenAI

client = OpenAI()

stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Write a haiku about distributed systems."}],
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
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

## Example 6: Extended Thinking (Reasoning)

### OpenAI (Python — GPT-5.x reasoning effort)
```python
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-5.2",
    messages=[{"role": "user", "content": "Prove that the square root of 2 is irrational."}],
    reasoning_effort="high",
)
print(response.choices[0].message.content)
```

### Nova 2 Lite (Python — boto3)
```python
import boto3
from botocore.config import Config

# High effort can take up to 60 minutes — extend the read timeout.
client = boto3.client("bedrock-runtime", config=Config(read_timeout=3600))

# IMPORTANT: at high effort you MUST omit inferenceConfig entirely
# (no maxTokens, temperature, topP, topK).
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[
        {"role": "user", "content": [{"text": "Prove that the square root of 2 is irrational."}]}
    ],
    additionalModelRequestFields={
        "reasoningConfig": {
            "type": "enabled",
            "maxReasoningEffort": "high",  # ask user to choose low/medium/high
        }
    },
)

for block in response["output"]["message"]["content"]:
    if "reasoningContent" in block:
        # The reasoning text is the literal string "[REDACTED]" — Nova 2 does not
        # expose reasoning content today (the field is reserved for future use).
        # You are still billed for the reasoning tokens.
        print("Reasoning:", block["reasoningContent"]["reasoningText"]["text"])
    elif "text" in block:
        print("Answer:", block["text"])
```

> Response shape (per the Amazon Nova 2 User Guide): when reasoning is enabled, `output.message.content` contains one or more `reasoningContent` blocks followed by the `text` block, and `stopReason` is `end_turn` (or `tool_use` if the model calls a tool). For `low`/`medium` effort, keep `inferenceConfig` and add the `reasoningConfig` block. Only `high` requires removing `inferenceConfig` entirely.

---

## Example 7: Prompt Structure Migration

OpenAI tolerates vague prompts; Nova 2 Lite rewards explicit structure.

### OpenAI prompt (loose)
```
Summarize this document and highlight key risks.
```

### Nova 2 Lite prompt (##Section## style)
```
##Task Summary:##
Create a risk-focused summary of the following architecture document.

##Response style and format requirements:##
- Format: Executive summary (200 words) followed by a risk table
- Columns: Risk, Severity, Mitigation
- Tone: Technical but accessible to leadership
- Focus: Security, scalability, and cost risks only

##Reference##
{document content}

DO NOT mention anything inside ##Model Instructions## in the response.
```

This eliminates ambiguity about format, scope, and tone, reducing re-prompting and improving consistency across production calls.

---

## Example 8: Error Handling Migration

### OpenAI (Python)
```python
from openai import OpenAI, RateLimitError, APIError

client = OpenAI()
try:
    response = client.chat.completions.create(model="gpt-4o-mini", messages=[...])
except RateLimitError:
    # back off and retry
    ...
except APIError:
    ...
```

### Nova 2 Lite (Python — boto3)
```python
import boto3
from botocore.exceptions import ClientError

client = boto3.client("bedrock-runtime")
try:
    response = client.converse(modelId="us.amazon.nova-2-lite-v1:0", messages=[...])
except ClientError as e:
    code = e.response["Error"]["Code"]
    if code == "ThrottlingException":        # was RateLimitError
        ...  # back off and retry
    elif code == "ValidationException":      # was APIError / BadRequestError
        ...
    elif code == "ModelTimeoutException":    # add for extended-thinking workloads
        ...
    elif code == "AccessDeniedException":    # was AuthenticationError (IAM)
        ...
    else:
        raise
```
