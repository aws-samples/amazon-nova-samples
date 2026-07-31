---
name: nova-api-migration-openai
description: Source guide for migrating OpenAI Python API code to Amazon Nova 2 Lite. Covers Chat Completions API, Responses API, Assistants API, and OpenAI models hosted on Amazon Bedrock (GPT-5.5/5.4, gpt-oss). Pairs with ../references/nova-target.md for the Nova side.
tags: [skill, migration, openai, gpt, gpt-oss, api, nova, bedrock]
---

# OpenAI → Nova 2 Lite (API Source Guide)

Covers the **OpenAI API source side**. For everything on the Nova side — model IDs, inference-config tables, reasoning effort rules, tool shape, structured output, streaming, and the validation checklist — read **`../references/nova-target.md`**. This file does not repeat them.

## Two Source Situations

1. **OpenAI API** (`api.openai.com`) — the customer calls GPT models through the `openai` SDK. Full migration: SDK swap, auth change (API key → IAM), request/response reshaping.
2. **OpenAI on Amazon Bedrock** — the customer already runs OpenAI models on Bedrock (GPT-5.5/5.4 via the Responses API, or gpt-oss via Converse/Responses/Chat Completions). Auth/Region/billing are already AWS-native, so this is usually lower-effort. See `references/openai-on-bedrock-patterns.md`.

## Key API Differences

1. **SDK**: `openai` → `boto3` Bedrock Runtime `converse`
2. **Auth**: API key (`OPENAI_API_KEY`) → AWS IAM credentials (role, profile, env vars)
3. **System prompt**: `role: "system"` message in array → dedicated `system=[{"text": ...}]` param
4. **Message content**: Flat string → typed content blocks (`[{"text": "..."}]`)
5. **Inference params**: Top-level `max_tokens`, `temperature`, `top_p` → nested `inferenceConfig` (camelCase: `maxTokens`, `topP`)
6. **Structured output**: Native `response_format` (JSON schema) → tool-forcing or inline schema
7. **Reasoning**: `reasoning_effort` (GPT-5.x) → `additionalModelRequestFields.reasoningConfig`
8. **Multimodal images**: URL or base64 → raw binary bytes; media MUST precede text
9. **Streaming**: `stream=True` param → separate `converse_stream()` method

### What Cannot Be Migrated Directly

- Assistants API threads / persistent state → Manage conversation history externally
- Built-in code interpreter (Assistants) → Use Nova's `nova_code_interpreter` built-in tool
- Built-in file search / retrieval (Assistants) → Use Amazon Bedrock Knowledge Bases
- Image generation (DALL-E / `gpt-image`) → Use Amazon Nova Canvas (separate model)
- Text-to-speech / Whisper → Use Amazon Polly / Amazon Transcribe
- Realtime API (voice) → Use Amazon Nova Sonic
- Fine-tuned OpenAI models → Re-run customization on Nova via Amazon Bedrock
- Web search built-in tool → Use Nova's `nova_grounding` built-in tool

## Migration Workflow

Follow these steps in order. Confirm findings with the user after each step.

### Step 1: Analyze the OpenAI Code

**First, identify WHERE the model runs:**
- [ ] **OpenAI API** (`api.openai.com`) — plain `OpenAI(api_key=...)` with no Bedrock base URL. Full migration.
- [ ] **OpenAI on Amazon Bedrock** — an `openai` client pointed at a `bedrock-mantle` base URL, the `BedrockOpenAI` client, or `boto3` `converse`/`invoke_model` with an `openai.*` model ID. Read `references/openai-on-bedrock-patterns.md` for the specific paths.

Then identify the API style:
- [ ] Chat Completions API — `client.chat.completions.create(...)` (most common)
- [ ] Responses API — `client.responses.create(...)` (newer; `input=` + `instructions=`)
- [ ] Assistants API — `client.beta.assistants.create(...)` / `client.beta.threads.*` (stateful)

Then identify which features are used:
- [ ] Basic text generation
- [ ] System prompt / instructions
- [ ] Multi-turn conversation (message history or threads)
- [ ] Function calling / tools
- [ ] Structured output (`response_format`, JSON mode)
- [ ] Multimodal (images)
- [ ] Streaming
- [ ] Reasoning effort (GPT-5.x `reasoning_effort`)
- [ ] Built-in tools (code interpreter, file search, web search)

Flag any features in the "cannot migrate" list and inform the user of alternatives before proceeding.

If the source model is a high-capability reasoning model (`gpt-5.5`, `gpt-5.4`, `o3`, `o1`) at high reasoning effort, you **MUST** ask whether the user has evaluated Nova 2 Lite for their use case.

### Step 2: Classify the Use Case

**Reasoning support by OpenAI model:**

| OpenAI Model | Native Reasoning Effort |
|--------------|------------------------|
| `gpt-4o` / `gpt-4o-mini` | No |
| `gpt-4.1` / `gpt-4.1-mini` | No |
| `gpt-4` / `gpt-3.5-turbo` | No |
| `gpt-5` / `gpt-5.2` | Yes — `reasoning_effort` parameter |
| `o1` / `o3` | Yes — reasoning models |

**Migration rules for reasoning:**
- Source does NOT support reasoning → omit `additionalModelRequestFields` entirely
- Source supports reasoning but it's NOT enabled → omit `additionalModelRequestFields`
- Reasoning IS enabled → ask the user which Nova effort level (see nova-target.md)

> Do NOT map OpenAI's effort level directly to Nova's by name. They are not numerically equivalent. Default to Nova `low` first, then increase only if evaluation shows quality gaps.

Then pick the Nova use-case type and inference config from **nova-target.md**.

### Step 3: Migrate the Code

You **MUST** read `references/feature-mapping.md` for the complete field mapping table.
You **SHOULD** read `references/code-examples.md` for before/after patterns.

If the source runs on **OpenAI hosted on Amazon Bedrock**, read `references/openai-on-bedrock-patterns.md` — the gpt-oss-on-Converse case is nearly a one-line `modelId` swap.

**SDK transformation (Chat Completions → Converse):**
```python
# OpenAI
from openai import OpenAI
client = OpenAI(api_key="...")
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
    ],
    max_tokens=1024,
    temperature=0.7,
)
print(response.choices[0].message.content)

# Nova 2 Lite
import boto3
client = boto3.client("bedrock-runtime", region_name="us-east-1")
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a helpful assistant."}],
    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
)
print(response["output"]["message"]["content"][0]["text"])
```

**Key transformations:**
- Remove `OpenAI(api_key=...)` — boto3 uses AWS credential chain
- Extract `{"role": "system", "content": "..."}` from messages → `system=[{"text": "..."}]`
- Wrap message content strings in typed blocks: `"content": "text"` → `"content": [{"text": "text"}]`
- `max_tokens` → `inferenceConfig.maxTokens`
- `temperature` → `inferenceConfig.temperature`
- `top_p` → `inferenceConfig.topP`
- `stop` → `inferenceConfig.stopSequences`
- `response.choices[0].message.content` → `response["output"]["message"]["content"][0]["text"]`
- `reasoning_effort="high"` → `additionalModelRequestFields={"reasoningConfig": {...}}` (only when enabled)

**Responses API transformation:**
```python
# OpenAI Responses API
response = client.responses.create(
    model="gpt-5",
    input="Explain quantum computing",
    instructions="You are a physics professor.",
    reasoning={"effort": "medium"},
)

# Nova 2 Lite
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a physics professor."}],
    messages=[{"role": "user", "content": [{"text": "Explain quantum computing"}]}],
    inferenceConfig={"temperature": 0.7},
    additionalModelRequestFields={
        "reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}
    },
)
```

### Step 4: Migrate Structured Output

If the source uses `response_format` (JSON mode or JSON schema), apply this step.

- `response_format={"type": "json_object"}` → inline JSON instruction in prompt + `temperature=0`
- `response_format={"type": "json_schema", "json_schema": {...}}` or Pydantic model → tool-forcing for complex schemas, inline prompt for simple ones

### Step 5: Migrate Tool Calling

Key mappings:
- `tools=[{"type": "function", "function": {...}}]` → `toolConfig={"tools": [{"toolSpec": {...}}]}`
- `function.name` → `toolSpec.name`
- `function.description` → `toolSpec.description`
- `function.parameters` (JSON Schema) → `toolSpec.inputSchema.json` (JSON Schema — structurally compatible, just re-wrap)
- `tool_choice` (`auto`/`required`/`none`/named) → `toolChoice` (`auto`/`any`/`tool`)
- Response: `tool_calls[].function` → `toolUse` content block
- Send back: `{"role": "tool", "tool_call_id": ..., "content": ...}` → `toolResult` in a user-role message

**OpenAI `tool_choice` mapping:**

| OpenAI `tool_choice` | Nova `toolChoice` |
|---------------------|-------------------|
| `"auto"` | `{"auto": {}}` |
| `"required"` | `{"any": {}}` |
| `"none"` | Remove `toolConfig` entirely |
| `{"type": "function", "function": {"name": "X"}}` | `{"tool": {"name": "X"}}` |

### Step 6: Present the Result

```
## Migrated Code

**Source:** OpenAI ({model name}) via {API style}
**Use case:** {type}
**Inference config:** temperature={T}, reasoning={enabled/disabled}
**Breaking changes:** {list any features that couldn't be migrated 1:1}

### Code
{complete migrated code}

### Implementation Notes
- {inference config rationale}
- {any multimodal ordering requirements}
- {features requiring alternative approach}
- For prompt optimization, use the nova-prompter skill
```

### Step 7: Validate

Run the **nova-target.md validation checklist**, plus these OpenAI-specific checks:
- [ ] No `openai` imports remain
- [ ] No `OPENAI_API_KEY` / `OpenAI(...)` client remains
- [ ] System prompt extracted from messages into `system=[{"text": ...}]`
- [ ] All message content wrapped in typed blocks (no flat strings)
- [ ] Inference params nested in `inferenceConfig` with camelCase (not top-level)
- [ ] `response_format` replaced with tool-forcing or inline schema
- [ ] `tool_choice` mapped to `toolChoice` (different structure)
- [ ] `response.choices[0].message.content` → dict-style response parsing
- [ ] Images converted from URL/base64 to raw bytes; media before text
- [ ] Error handling updated (`RateLimitError` → `ThrottlingException`, etc.)
- [ ] High effort: `inferenceConfig` removed entirely, `read_timeout=3600` set

## Quick Reference

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `openai` SDK | `boto3` bedrock-runtime |
| `client.chat.completions.create()` / `client.responses.create()` | `client.converse()` |
| `OPENAI_API_KEY` | AWS IAM credentials |
| `model="gpt-4o-mini"` | `modelId="us.amazon.nova-2-lite-v1:0"` |
| `{"role": "system", "content": "..."}` in messages | `system=[{"text": "..."}]` |
| `{"content": "text"}` | `{"content": [{"text": "text"}]}` |
| `max_tokens` / `temperature` / `top_p` (top-level) | `inferenceConfig.maxTokens` / `.temperature` / `.topP` |
| `tools=[{"type": "function", ...}]` | `toolConfig={"tools": [{"toolSpec": ...}]}` |
| `tool_choice` | `toolChoice` |
| `response_format` (JSON schema) | Tool-forcing or inline prompt schema |
| `reasoning_effort="high"` | `additionalModelRequestFields={"reasoningConfig": {...}}` |
| `stream=True` | `client.converse_stream()` |
| `response.choices[0].message.content` | `response["output"]["message"]["content"][0]["text"]` |

## Common Mistakes

### Leaving the system prompt as a message
**Problem:** Keeping `{"role": "system", ...}` in the `messages` array — Bedrock rejects system as a role.
**Fix:** Extract into the dedicated `system=[{"text": ...}]` parameter.

### Forgetting to wrap content in typed blocks
**Problem:** Passing `{"content": "hello"}` — Bedrock requires typed content blocks.
**Fix:** Wrap as `{"content": [{"text": "hello"}]}`.

### Leaving inference params at the top level
**Problem:** Passing `max_tokens`/`temperature`/`top_p` as top-level arguments.
**Fix:** Nest in `inferenceConfig` with camelCase (`maxTokens`, `temperature`, `topP`).

### Passing `inferenceConfig` with high-effort reasoning
**Problem:** Including any inference config params when `maxReasoningEffort` is `high`.
**Fix:** Remove the entire `inferenceConfig` block at high effort and set `read_timeout=3600`.

### Passing image URLs directly
**Problem:** Using OpenAI's `{"type": "image_url", "image_url": {"url": "..."}}` format.
**Fix:** Download the image and pass raw bytes: `{"image": {"format": "jpeg", "source": {"bytes": image_bytes}}}`. Media must precede text.
