# OpenAI on Amazon Bedrock → Nova 2 Lite

Covers the case where the customer already runs OpenAI models on Amazon Bedrock and wants to migrate to Nova 2 Lite — a common step in multi-model bake-offs.

The migration is usually **lower-effort** because auth, Region, and billing are already AWS-native. What changes is the API surface and model ID.

---

## Two Classes of OpenAI-on-Bedrock Model

| Class | Example Model IDs | APIs Supported | Endpoint |
|-------|-------------------|----------------|----------|
| **Proprietary (GPT-5.x)** | `openai.gpt-5.5`, `openai.gpt-5.4` | Responses API only | `bedrock-mantle` (OpenAI-compatible) |
| **Open weights (gpt-oss)** | `openai.gpt-oss-120b-1:0`, `openai.gpt-oss-20b-1:0` | Converse, InvokeModel, Responses, Chat Completions | both `bedrock-runtime` and `bedrock-mantle` |

**Implications:**
1. **gpt-oss on Converse** → migration is nearly trivial: change `modelId` and adjust the prompt. See Path A.
2. **GPT-5.x on Responses API** → must move from the Responses shape to native Converse API. See Path B.

---

## Source Detection

### Responses API via bedrock-mantle (GPT-5.5/5.4 or gpt-oss)
```python
# Standard OpenAI SDK + Bedrock base URL
from openai import OpenAI
client = OpenAI(
    base_url="https://bedrock-mantle.us-east-2.api.aws/openai/v1",
    api_key="<BEDROCK_API_KEY>",
)
response = client.responses.create(
    model="openai.gpt-5.5",
    input=[
        {"role": "developer", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Summarize cloud computing."},
    ],
    reasoning={"effort": "medium"},
)

# Or: dedicated BedrockOpenAI client
from openai import BedrockOpenAI
client = BedrockOpenAI(aws_region="us-east-2")
response = client.responses.create(model="openai.gpt-5.5", input="...")
```

### gpt-oss via Converse (bedrock-runtime)
```python
import boto3
client = boto3.client("bedrock-runtime", region_name="us-east-1")
response = client.converse(
    modelId="openai.gpt-oss-120b-1:0",
    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
)
```

### gpt-oss via Chat Completions (bedrock-mantle)
```python
from openai import OpenAI
client = OpenAI(
    base_url="https://bedrock-mantle.us-east-1.api.aws/openai/v1",
    api_key="<BEDROCK_API_KEY>",
)
response = client.chat.completions.create(
    model="openai.gpt-oss-120b",
    messages=[{"role": "user", "content": "Hello"}],
)
```

---

## Path A: gpt-oss on Converse → Nova (Trivial)

If the customer already uses `boto3` `converse` with a `gpt-oss` model ID, migration is a model swap:

```python
# Before
response = client.converse(
    modelId="openai.gpt-oss-120b-1:0",
    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
    inferenceConfig={"temperature": 0.7, "maxTokens": 1024},
)

# After — just swap modelId
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
    inferenceConfig={"temperature": 0.7, "maxTokens": 1024},
)
```

Additional changes only needed if:
- Adding reasoning: include `additionalModelRequestFields={"reasoningConfig": {...}}`
- Using tools: verify `toolConfig` shape matches Nova's expectations (it should — Converse API is model-agnostic)
- Prompt optimization: use the nova-prompter power separately

---

## Path B: GPT-5.x Responses API → Nova Converse

This is a more substantial migration — the SDK, endpoint, and request/response shape all change.

### SDK & Client
```python
# Before: OpenAI SDK → bedrock-mantle
from openai import OpenAI  # or BedrockOpenAI
client = OpenAI(base_url="https://bedrock-mantle.us-east-2.api.aws/openai/v1", api_key="...")

# After: boto3 → bedrock-runtime
import boto3
client = boto3.client("bedrock-runtime", region_name="us-east-1")
```

### Request Shape
```python
# Before: Responses API
response = client.responses.create(
    model="openai.gpt-5.5",
    input=[
        {"role": "developer", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain microservices."},
    ],
    reasoning={"effort": "medium"},
    max_output_tokens=1024,
    temperature=0.7,
)
print(response.output_text)

# After: Converse API
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a helpful assistant."}],
    messages=[{"role": "user", "content": [{"text": "Explain microservices."}]}],
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
    additionalModelRequestFields={
        "reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}
    },
)
print(response["output"]["message"]["content"][0]["text"])
```

### Key Mappings (Responses API → Converse)

| Responses API (on Bedrock) | Nova Converse |
|---------------------------|---------------|
| `model="openai.gpt-5.5"` | `modelId="us.amazon.nova-2-lite-v1:0"` |
| `input=[{"role": "developer", ...}, {"role": "user", ...}]` | `system=[{"text": ...}]` + `messages=[...]` |
| `{"role": "developer", "content": "..."}` | `system=[{"text": "..."}]` |
| `{"role": "user", "content": "..."}` | `messages=[{"role": "user", "content": [{"text": "..."}]}]` |
| `reasoning={"effort": "medium"}` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}}` |
| `max_output_tokens` | `inferenceConfig={"maxTokens": ...}` |
| `temperature` | `inferenceConfig={"temperature": ...}` |
| `response.output_text` | `response["output"]["message"]["content"][0]["text"]` |

---

## Path C: gpt-oss on Chat Completions (bedrock-mantle) → Nova Converse

Similar to migrating from the OpenAI API, but auth is already AWS-native.

```python
# Before: Chat Completions on bedrock-mantle
from openai import OpenAI
client = OpenAI(base_url="https://bedrock-mantle.us-east-1.api.aws/openai/v1", api_key="...")
response = client.chat.completions.create(
    model="openai.gpt-oss-120b",
    messages=[
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
    ],
    max_tokens=1024,
)

# After: Native Converse
import boto3
client = boto3.client("bedrock-runtime", region_name="us-east-1")
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are helpful."}],
    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
    inferenceConfig={"maxTokens": 1024},
)
```

Changes needed:
- SDK: `openai` → `boto3`
- System: extract from messages → `system` param
- Content: string → typed blocks
- Inference: top-level → nested `inferenceConfig`
- Auth: Bedrock API key → standard AWS credential chain (may already be configured)
