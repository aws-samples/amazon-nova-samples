---
name: nova-migration-gemini
description: Source guide for migrating Google Gemini 2.0/2.5/3.x Python code and prompts to Amazon Nova 2 Lite. Read after nova-migration routes a Gemini source here. Covers google-genai / google-generativeai SDK detection, Interactions API, and the full Gemini→Nova feature mapping. Pairs with ../references/nova-target.md for the Nova side.
tags: [skill, migration, gemini, nova, bedrock]
---

# Gemini → Nova 2 Lite (source guide)

Covers the **Gemini source side**. For everything on the Nova side — model IDs, inference-config
tables, reasoning effort rules, `##Section##` prompt format, tool shape, structured output, and the
validation checklist — read **`../references/nova-target.md`**. This file does not repeat them.

## Gemini-side key differences

1. **SDK**: `google-genai` / `google-generativeai` → `boto3` Bedrock Runtime `converse`
2. **Prompt format**: XML tags / free-form → `##Section Name##` (see nova-target)
3. **Multimodal system prompt**: Full instructions allowed (Gemini) → Persona-only (Nova)
4. **Structured output**: Native `response_mime_type` + `response_schema` → tool-forcing / inline schema
5. **Stateful turns**: `previous_interaction_id` → pass full message history
6. **Media ordering**: any order → media MUST precede text

### What cannot be migrated directly

- Managed agents / Antigravity → build with tool use + orchestration
- Deep Research agent → no equivalent
- Image generation → Amazon Nova Canvas (separate model)
- Speech/TTS → Amazon Polly
- Code execution tool → `amazon.nova_code_interpreter` built-in, or custom executor via tool calling
- Interaction persistence (`store=true`) → manage state externally

## Workflow

Follow in order; confirm findings with the user after each step.

### Step 1: Analyze the Gemini code

Identify the SDK / API style:
- [ ] Deprecated SDK (`import google.generativeai as genai`) — `GenerativeModel`, `generate_content`
- [ ] Current SDK (`from google import genai`) with `generateContent` — `client.models.generate_content`
- [ ] Current SDK with Interactions API — `client.interactions.create`

Identify features used: basic text, system instructions, multi-turn, function calling, structured
output, multimodal, streaming, reasoning/thinking, agents.

You **MUST** flag any "cannot migrate" features and offer the alternative before proceeding.

If the source is a Gemini "pro" variant (`gemini-2.5-pro`, `gemini-3.1-pro-preview`), you **MUST**
ask whether the user has evaluated Nova 2 Lite for their use case — pro-tier models have higher
capability ceilings.

### Step 2: Classify the use case

**Native thinking support by Gemini model:**

| Gemini Model | Native Thinking |
|--------------|-----------------|
| `gemini-2.0-flash` / `gemini-2.0-flash-lite` | No — any CoT is prompt text |
| `gemini-2.5-flash` / `gemini-2.5-pro` | Yes — `thinking_config` / `thinking` |
| `gemini-3.5-flash` / `gemini-3.1-pro-preview` | Yes |

Thinking migration rules:
- Source has no native thinking, OR thinking not enabled → reasoning **disabled** (omit
  `additionalModelRequestFields`). If the prompt uses CoT ("think step by step"), keep that text.
- Thinking IS enabled → enable Nova reasoning and ask the user which effort level (see
  nova-target "Reasoning"). Do NOT copy Gemini's `budget_tokens` directly.

Then pick the Nova use-case type and inference config from **nova-target.md → "Inference config by
use case"**.

### Step 3: Migrate the code

You **MUST** read `references/feature-mapping.md` for the complete Gemini→Nova mapping table.
You **SHOULD** read `references/code-examples.md` for before/after patterns.

If the source uses `generateContent` (either SDK) or the Interactions API
(`client.interactions.create`), you **MUST** also read `references/generate-content-patterns.md`
for the specific parameter mappings, Interactions API patterns, and deprecated SDK handling.

Ask which region model ID to use (default `us.amazon.nova-2-lite-v1:0`) — see nova-target.

**SDK transformation:**
```python
# Gemini
from google import genai
client = genai.Client()
interaction = client.interactions.create(model="gemini-3.5-flash", ...)

# Nova 2 Lite
import boto3
client = boto3.client("bedrock-runtime")
response = client.converse(modelId="us.amazon.nova-2-lite-v1:0", ...)
```

Include `additionalModelRequestFields` ONLY when reasoning is enabled (see nova-target).

### Step 4: Migrate the prompt

Apply the `##Section##` transformations from **nova-target.md → "Prompt format"**. Gemini-specific
note: replace `<context>`/`<task>`/`<instructions>`/`<examples>` XML tags, and convert any
free-form section naming to the canonical Nova section names.

### Step 5: Structured output

Gemini's `response_mime_type` + `response_schema` → inline schema (simple) or tool-forcing
(complex). See nova-target "Structured output" and `references/code-examples.md` Example 3.

### Step 6: Tool calling

Gemini → Nova specifics (target shape is in nova-target "Tool use"):
- `function_declarations` → `toolSpec`
- `parameters` (**OpenAPI** schema) → `inputSchema.json` (**JSON Schema** — convert, don't copy)
- `tool_config.mode` (`AUTO`/`ANY`/`NONE`) → `toolChoice` (`auto`/`any`/`tool`)

### Step 7: Present the result

Use the output format in **nova-target.md** (Migrated Code → use case, inference config, breaking
changes, code, prompt, implementation notes).

### Step 8: Validate

Run the **nova-target.md validation checklist**, plus this Gemini-specific check:
- [ ] No Gemini-specific surface remains (`previous_interaction_id`, `store`, OpenAPI tool schemas)

## Quick reference

| Gemini | Nova 2 Lite |
|--------|-------------|
| `google-genai` | `boto3` bedrock-runtime |
| `client.models.generate_content()` / `client.interactions.create()` | `client.converse()` |
| `system_instruction=` | `system=[{"text": "..."}]` |
| `config=GenerateContentConfig(tools=[...])` | `toolConfig={"tools": [{toolSpec}]}` |
| `response_mime_type` + `response_schema` | tool-forcing or inline prompt schema |
| `thinking_config=ThinkingConfig(thinking_budget=N)` | `additionalModelRequestFields={"reasoningConfig": {...}}` |
| `client.models.generate_content_stream()` | `client.converse_stream()` |
| XML tags in prompt | `##Section Name##` delimiters |

## Common mistakes

- **Full system instructions in multimodal calls** — move everything except persona to the user prompt.
- **`additionalModelRequestFields` when reasoning is disabled** — omit it entirely.
- **XML tags left in the prompt** — Nova ignores them; convert to `##Section##`.
- **Text before media** — media blocks MUST come first.
- **OpenAPI tool schema copied as-is** — convert to JSON Schema in `inputSchema.json`.
