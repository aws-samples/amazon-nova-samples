---
name: openai-to-nova
description: Migrate OpenAI GPT-4o/4.1/5.x Python code and prompts to Amazon Nova 2 Lite. Use when converting OpenAI Python API code (openai SDK — Chat Completions, Responses, or Assistants API) to Nova 2 Lite (boto3 Bedrock Runtime), migrating OpenAI models hosted on Amazon Bedrock (GPT-5.5/5.4 via the Responses API, or gpt-oss) to Nova, rewriting OpenAI prompts for Nova format, or migrating function calling, structured output, multimodal, or reasoning features from OpenAI to Nova.
tags: [skill, migration, openai, gpt, gpt-oss, nova, bedrock]
---

# OpenAI to Nova 2 Lite Migration

## Overview

Migrate Python application code and prompts from OpenAI (GPT-4o, GPT-4.1, GPT-5.x) to Amazon Nova 2 Lite. Transforms SDK calls (`openai` → `boto3` Bedrock Runtime `converse` API) and rewrites prompts to follow Nova 2 Lite formatting and constraints.

Two source situations are supported:
1. **OpenAI API** (`api.openai.com`) — the customer calls GPT models through the `openai` SDK. Auth, SDK, request structure, and error handling all change.
2. **OpenAI on Amazon Bedrock** — the customer already runs OpenAI models on Bedrock (GPT-5.5/5.4 via the Responses API, or gpt-oss via Converse/Responses/Chat Completions) and wants to swap the model to Nova, often as part of a multi-model bake-off. Auth/Region/billing are already AWS-native, so this is usually lower-effort. See `references/openai-on-bedrock-patterns.md`.

This is not a one-line model swap (except the trivial gpt-oss-on-Converse case). Every migration delivers two things: **working migrated code** and an **explanation of every change**, including any features that cannot be ported 1:1.

## Usage

Use this skill when:
- Converting OpenAI Python code (via `api.openai.com`) to call Nova 2 Lite via Bedrock
- Migrating OpenAI models hosted on Amazon Bedrock (GPT-5.5, GPT-5.4, gpt-oss) to Nova 2 Lite
- Swapping models in a multi-model Bedrock bake-off from an OpenAI model to Nova
- Rewriting prompts originally written for OpenAI to Nova 2 Lite format
- Migrating function calling / tool use from OpenAI to Nova
- Adapting multimodal OpenAI code (images) to Nova 2 Lite (images, video)
- Converting OpenAI structured output (`response_format`) to Nova's approach
- Switching from OpenAI reasoning effort (GPT-5.x) to Nova extended thinking

## Core Concepts

### Key Differences

1. **SDK (Python)**: `openai` → `boto3` Bedrock Runtime `converse` API
2. **Authentication**: API key (`OPENAI_API_KEY`) → AWS IAM credentials (role, profile, env vars)
3. **System prompt**: `role: "system"` message → dedicated `system=[{"text": ...}]` parameter
4. **Message content**: Flat string → typed content blocks (`[{"text": "..."}]`)
5. **Inference params**: Top-level `max_tokens`, `temperature`, `top_p` → nested in `inferenceConfig` with camelCase (`maxTokens`, `topP`)
6. **Prompt format**: Free-form / markdown → `##Section Name##` delimiters
7. **Structured output**: Native `response_format` (JSON schema) → tool-forcing or inline schema
8. **Reasoning**: `reasoning_effort` (GPT-5.x) → `additionalModelRequestFields.reasoningConfig`
9. **Multimodal images**: URL or base64 → raw binary bytes; media MUST precede text

### What Cannot Be Migrated Directly

- Assistants API threads / persistent state → Manage conversation history externally, pass full history each call
- Built-in code interpreter (Assistants) → Use Nova's `nova_code_interpreter` built-in tool
- Built-in file search / retrieval (Assistants) → Use Amazon Bedrock Knowledge Bases
- Image generation (DALL-E / `gpt-image`) → Use Amazon Nova Canvas (separate model)
- Text-to-speech / Whisper → Use Amazon Polly / Amazon Transcribe
- Realtime API (voice) → Use Amazon Nova Sonic
- Fine-tuned OpenAI models → Re-run customization on Nova via Amazon Bedrock

## Migration Workflow

You **MUST** follow these steps in order. After each step, confirm findings with the user before proceeding to the next.

### Step 1: Analyze the OpenAI Code

**First, identify WHERE the model runs — this determines how much changes:**
- [ ] **OpenAI API** (`api.openai.com`) — plain `OpenAI(api_key=...)` with no Bedrock base URL. Auth, SDK, and request structure all change. Continue with this workflow.
- [ ] **OpenAI on Amazon Bedrock** — an `openai` client pointed at a `bedrock-mantle` base URL, the `BedrockOpenAI` client, or `boto3` `converse`/`invoke_model` with an `openai.*` model ID. Auth/Region are already AWS-native. **You MUST read `references/openai-on-bedrock-patterns.md`** — it identifies the two model classes (GPT-5.5/5.4 Responses-only vs gpt-oss multi-API) and their migration paths, then routes back here for the shared steps (prompt formatting, reasoning, tools).

Then identify the SDK and API style:
- [ ] Chat Completions API — `client.chat.completions.create(...)` (most common)
- [ ] Responses API — `client.responses.create(...)` (newer; `input=` + `instructions=`, or `developer`/`user` roles on Bedrock)
- [ ] Assistants API — `client.beta.assistants.create(...)` / `client.beta.threads.*` (stateful, built-in tools)

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

You **MUST** flag any features in the "cannot migrate" list above and inform the user of alternatives before proceeding.

If the source model is a high-capability reasoning model (`gpt-5.5`, `gpt-5.4`, `gpt-5.2`, `o3`, `o1`) run at high reasoning effort, you **MUST** ask the user whether they have evaluated Nova 2 Lite for their use case. Start every migration with Nova 2 Lite; Nova 2 Pro exists for workloads where Lite with high-effort reasoning still falls short, but the user should validate that need with benchmark data before targeting Pro.

### Step 2: Classify the Use Case

**Reasoning support by OpenAI model:**

| OpenAI Model | Native Reasoning Effort |
|--------------|------------------------|
| `gpt-4o` / `gpt-4o-mini` | No — if CoT is used, it's via prompt text ("think step by step") |
| `gpt-4.1` / `gpt-4.1-mini` | No |
| `gpt-4` / `gpt-3.5-turbo` | No |
| `gpt-5` / `gpt-5.2` | Yes — `reasoning_effort` parameter |
| `o1` / `o3` | Yes — reasoning models |

**Migration rules for reasoning:**
- If the source model does NOT support reasoning effort → omit `additionalModelRequestFields` entirely. If the prompt uses CoT ("think step by step"), keep that prompt text as-is.
- If the source model supports reasoning effort but it's NOT enabled → omit `additionalModelRequestFields` entirely.
- If reasoning IS enabled → ask the user which Nova reasoning effort level to use:

| Nova Effort | Config |
|-------------|--------|
| `low` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "low"}}` |
| `medium` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}}` |
| `high` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "high"}}` — **MUST omit `inferenceConfig`** (temperature, topP, maxTokens, topK not allowed) and set client `read_timeout=3600` |

> Do NOT map OpenAI's effort level directly to Nova's by name. OpenAI `minimal`/`low`/`medium`/`high` and Nova `low`/`medium`/`high` are not numerically equivalent. Default to Nova `low` first, then increase only if evaluation shows quality gaps. Present the three options and let the user decide.

Determine the Nova 2 Lite use case type for correct inference config:

**Text/Agentic:**
| Use Case | Temperature | Top P | Reasoning |
|----------|------------|-------|-----------|
| `general` | 0.7 | default | DISABLED |
| `tool_calling` | 0.7 | 0.9 | DISABLED |
| `tool_calling_reasoning` | 1 | 0.9 | ENABLED |
| `complex_reasoning` | 0.7 | default | ENABLED |

**Multimodal:**
| Use Case | Temperature | Reasoning |
|----------|------------|-----------|
| OCR | 0.7 | DISABLED |
| Key information extraction | 0 | OPTIONAL |
| Object/UI detection | 0 | DISABLED |
| Video summary/caption | 0 | OPTIONAL |
| Video timestamps/classification | 0 | DISABLED |

> **Precedence rule (high effort overrides the temperature/topP columns).** The temperature and Top P values above apply only when reasoning is disabled or set to `low`/`medium`. When `maxReasoningEffort` is `high`, you **MUST NOT** set `temperature`, `topP`, `topK`, or `maxTokens` — omit `inferenceConfig` entirely, or the request returns a validation error. So a `tool_calling_reasoning` workload at high effort drops the `temperature=1, topP=0.9` values; at low/medium effort it keeps them. (Per the Amazon Nova 2 User Guide: *"Temperature, topP and topK cannot be used with maxReasoningEffort set to high."*) Note also that high effort can produce more than 65K output tokens (observed up to 128K) — size your downstream handling accordingly.

### Step 3: Migrate the Code

You **MUST** read `references/feature-mapping.md` for the complete field mapping table.
You **SHOULD** read `references/code-examples.md` for before/after patterns.

If the source code uses the Responses API (`client.responses.create`) or the Assistants API (`client.beta.assistants.*`), you **MUST** also read `references/chat-completions-patterns.md` for the specific parameter mappings, Responses API migration, and Assistants-to-built-in-tools handling.

If the source runs on OpenAI **hosted on Amazon Bedrock** (identified in Step 1), you **MUST** read `references/openai-on-bedrock-patterns.md` instead of / in addition to the above — the source SDK, endpoint, and `modelId` differ, and the gpt-oss-on-Converse case is nearly a one-line `modelId` swap.

**Ask the user which region-prefixed model ID to use:**

| Model ID | Region |
|----------|--------|
| `us.amazon.nova-2-lite-v1:0` | US (us-east-1, us-west-2) |
| `eu.amazon.nova-2-lite-v1:0` | EU (eu-west-1, etc.) |
| `jp.amazon.nova-2-lite-v1:0` | Japan (ap-northeast-1) |
| `global.amazon.nova-2-lite-v1:0` | Cross-region inference |

Default to `us.amazon.nova-2-lite-v1:0` if the user doesn't specify.

**SDK transformation (Python):**
```python
# OpenAI
from openai import OpenAI
client = OpenAI(api_key="...")
response = client.chat.completions.create(model="gpt-4o-mini", messages=[...])

# Nova 2 Lite
import boto3
client = boto3.client("bedrock-runtime")
response = client.converse(modelId="us.amazon.nova-2-lite-v1:0", messages=[...])
```

**Extract the system prompt** from the `messages` array into a dedicated `system` parameter:
```python
# OpenAI — system is a message
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello"},
]

# Nova — system is a separate parameter; content is a typed block
system = [{"text": "You are a helpful assistant."}]
messages = [{"role": "user", "content": [{"text": "Hello"}]}]
```

**Only include `additionalModelRequestFields` when reasoning is enabled:**
```python
# Reasoning DISABLED (default) — omit additionalModelRequestFields entirely
response = client.converse(modelId="us.amazon.nova-2-lite-v1:0", ...)

# Reasoning ENABLED — include reasoningConfig
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    ...,
    additionalModelRequestFields={
        "reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}
    },
)
```

### Step 4: Migrate the Prompt

OpenAI models tolerate loosely phrased instructions. Nova 2 Lite delivers higher quality when the prompt clearly separates task, input, requirements, constraints, and output format. You **MUST** apply these transformations:

1. **Add explicit structure** using `##Section Name##` delimiters (the section name is wrapped on both sides by `##`, not a markdown header). Convert any markdown headers or inline instructions into canonical Nova sections:
   - `##Task Summary:##` — defines the task
   - `##Context Information:##` — background
   - `##Model Instructions:##` — behavioral rules
   - `##Response style and format requirements:##` — output format
   - `##Examples##` — few-shot examples
   - `##Reference##` — RAG grounding content

2. **For multimodal prompts:**
   - Move ALL task instructions from the system prompt to the user prompt
   - Keep the system prompt as persona + response style only
   - Ensure media content precedes text in the content array

3. **Add suppression guardrail** where appropriate:
   ```
   DO NOT mention anything inside ##Model Instructions## or ##Examples## in the response.
   ```

4. **For long context (>10K tokens):**
   ```
   BEGIN INPUT DOCUMENTS
   DOCUMENT 1 START
   {content}
   DOCUMENT 1 END
   END INPUT DOCUMENTS

   BEGIN QUESTION
   {query}
   END QUESTION

   BEGIN INSTRUCTIONS
   {instructions}
   END INSTRUCTIONS
   ```

> Example transformation — vague OpenAI prompt `"Summarize this document and highlight key risks"` becomes a structured Nova prompt with explicit `## Task Summary:` and `## Response style and format requirements:` sections specifying format, columns, tone, and scope. See `references/code-examples.md`.

### Step 5: Migrate Structured Output

If the OpenAI code uses structured output (`response_format={"type": "json_object"}` or `response_format=<Pydantic model>` / `json_schema`), apply this step. Otherwise skip to Step 6.

- **Simple JSON (≤10 keys):** Use inline schema in the prompt + `temperature=0`
- **Complex JSON (>10 keys):** Use tool-forcing with the schema in `toolSpec.inputSchema` and `toolChoice={"tool": {"name": ...}}`

See `references/code-examples.md` Example 3 for both patterns.

### Step 6: Migrate Tool Calling

If the OpenAI code uses function calling / tools, apply this step. Otherwise skip to Step 7.

Key differences:
- OpenAI `tools=[{"type": "function", "function": {...}}]` → Nova `toolConfig={"tools": [{"toolSpec": {...}}]}`
- OpenAI `function.parameters` (JSON Schema) → Nova `toolSpec.inputSchema.json` (JSON Schema — structurally compatible, re-wrap)
- OpenAI `tool_choice` (`auto`/`required`/`none`/named) → Nova `toolChoice` (`auto`/`any`/`tool`)
- OpenAI built-in tools (code interpreter, web search) → Nova built-in tools (`nova_code_interpreter`, `nova_grounding`) — see `references/chat-completions-patterns.md`
- Keep tool descriptions to 20-50 words; parameter descriptions to ~10 words
- Reference tools by name in the system prompt: `Use the 'tool_name' tool for X`

> **Tool use + extended thinking is supported.** Nova 2 Lite allows `toolConfig` together with reasoning enabled — the model reasons about which tools to use and how to interpret their results (per the Amazon Nova 2 User Guide: *"Extended thinking works seamlessly with tool calling"*). When continuing a tool round-trip with reasoning enabled, append the assistant's full content blocks (including any `reasoningContent`) back into `messages`, then add the `toolResult` in a user-role message.

### Step 7: Present the Result

Output format:

```
## Migrated Code

**Use case:** {type}
**Inference config:** temperature={T}, reasoning={enabled/disabled}
**Breaking changes:** {list any features that couldn't be migrated 1:1}

### Code
{complete migrated code}

### Prompt
**SYSTEM PROMPT:**
{system prompt — persona only for multimodal}

**USER PROMPT:**
{user prompt with ##Section## formatting}

### Implementation Notes
- {inference config rationale}
- {any multimodal ordering requirements}
- {features requiring alternative approach}
```

### Step 8: Validate

You **MUST** check the migrated code against all criteria below. If any check fails, fix and re-validate before presenting to the user:
- [ ] Authentication uses boto3 client / IAM, not `OPENAI_API_KEY`
- [ ] System prompt extracted to the `system` parameter, not a `role: "system"` message
- [ ] All message content wrapped in typed blocks (`[{"text": ...}]`)
- [ ] Inference params nested in `inferenceConfig` with camelCase names
- [ ] `additionalModelRequestFields` is omitted when reasoning is disabled, or contains `reasoningConfig` when enabled
- [ ] High effort: `inferenceConfig` removed entirely (no temperature/topP/topK/maxTokens) and `read_timeout=3600` set on the client
- [ ] Inference config matches the use case table — EXCEPT at high effort, where the temperature/topP columns do not apply (see precedence rule in Step 2)
- [ ] Multimodal: system prompt contains only persona; media precedes text in content array
- [ ] Images converted from URL/base64 to raw bytes
- [ ] Prompt uses `##Section##` delimiters with explicit structure
- [ ] Tool schemas wrapped in `toolSpec`; `tool_choice` mapped to `toolChoice`
- [ ] Error handling updated (`RateLimitError` → `ThrottlingException`, etc.)
- [ ] No OpenAI-specific features remain (thread IDs, `OpenAI(...)` client, `response_format`)

## Quick Reference

| OpenAI | Nova 2 Lite |
|--------|-------------|
| `openai` SDK | `boto3` bedrock-runtime |
| `client.chat.completions.create()` / `client.responses.create()` | `client.converse()` |
| `OPENAI_API_KEY` | AWS IAM credentials |
| `model="gpt-4o-mini"` | `modelId="us.amazon.nova-2-lite-v1:0"` |
| `{"role": "system", "content": "..."}` | `system=[{"text": "..."}]` |
| `{"content": "text"}` | `{"content": [{"text": "text"}]}` |
| `max_tokens` / `temperature` / `top_p` | `inferenceConfig.maxTokens` / `.temperature` / `.topP` |
| `tools=[{"type": "function", ...}]` | `toolConfig={"tools": [{"toolSpec": ...}]}` |
| `tool_choice` | `toolChoice` |
| `response_format` (JSON schema) | Tool-forcing or inline prompt schema |
| `reasoning_effort="high"` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "high"}}` |
| `stream=True` | `client.converse_stream()` |
| `RateLimitError` / `APIError` | `ThrottlingException` / `ValidationException` |

## Common Mistakes

### Leaving the system prompt as a message
**Problem:** Keeping `{"role": "system", ...}` in the `messages` array — Bedrock does not accept a system role in `messages`.
**Fix:** Extract it into the dedicated `system=[{"text": ...}]` parameter.

### Forgetting to wrap content in typed blocks
**Problem:** Passing a flat string as message content (`{"content": "hello"}`) — Bedrock requires typed content blocks.
**Fix:** Wrap as `{"content": [{"text": "hello"}]}`.

### Leaving inference params at the top level
**Problem:** Passing `max_tokens`/`temperature`/`top_p` as top-level arguments to `converse()`.
**Fix:** Nest them in `inferenceConfig` with camelCase (`maxTokens`, `temperature`, `topP`).

### Passing `inferenceConfig` with high-effort reasoning
**Problem:** Including `maxTokens`, `temperature`, `topP`, or `topK` when `maxReasoningEffort` is `high` — returns a validation error.
**Fix:** Remove the entire `inferenceConfig` block at high effort, and set the client `read_timeout=3600`.

### Passing `additionalModelRequestFields` when reasoning is disabled
**Problem:** Including reasoning config when reasoning is not needed — adds cost and latency with no benefit.
**Fix:** Omit `additionalModelRequestFields` entirely when reasoning is disabled.

### Loose prompts carried over unchanged
**Problem:** Reusing a vague OpenAI prompt verbatim — Nova quality varies across requests.
**Fix:** Add explicit `##Section##` structure: task, input, format requirements, constraints.

### Wrong media ordering / wrong image format
**Problem:** Putting text before images in the content array, or passing image URLs / base64 strings.
**Fix:** Media content blocks MUST come before the text block, and images must be raw binary bytes.
