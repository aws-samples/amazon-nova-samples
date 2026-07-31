# Gemini → Nova 2 Lite (API Source Guide)

Covers the **Gemini API source side**. For everything on the Nova side — model IDs, inference-config tables, reasoning effort rules, tool shape, structured output, streaming, and the validation checklist — load the **`nova-target.md`** steering file (via `readSteering`). This file does not repeat them.

## SDK Detection

Identify which Gemini SDK the source uses:

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

## Key API Differences

1. **SDK**: `google-genai` / `google-generativeai` → `boto3` Bedrock Runtime `converse`
2. **Auth**: Google API key (`GOOGLE_API_KEY`) → AWS credentials (IAM role, profile, or env vars)
3. **System prompt**: `system_instruction=` param → dedicated `system=[{"text": "..."}]` param
4. **Message content**: `parts` with mixed types → typed content blocks (`[{"text": "..."}]`)
5. **Inference params**: `generation_config={...}` / `GenerateContentConfig(...)` → nested `inferenceConfig` (camelCase)
6. **Roles**: `model` → `assistant`
7. **Multimodal**: Media in any order → media MUST precede text
8. **Multi-turn state**: `previous_interaction_id` (server-side) → pass full message history
9. **Structured output**: Native `response_mime_type` + `response_schema` → tool-forcing or inline schema

### What Cannot Be Migrated Directly

- Managed agents / Antigravity → Build with tool use + orchestration
- Deep Research agent → No equivalent
- Image generation → Use Amazon Nova Canvas (separate model)
- Speech/TTS → Use Amazon Polly
- Code execution tool → Use Nova's `nova_code_interpreter` built-in tool
- Interaction persistence (`store=true`) → Manage state externally
- `genai.upload_file(...)` → Pass bytes inline or use S3 URI for large files
- Google Search grounding → Use Nova's `nova_grounding` built-in tool

## Migration Workflow

Follow these steps in order. Confirm findings with the user after each step.

### Step 1: Analyze the Gemini Code

Identify the SDK style (see SDK Detection above):
- [ ] Deprecated SDK (`import google.generativeai as genai`)
- [ ] Current SDK with `generateContent` (`client.models.generate_content`)
- [ ] Current SDK with Interactions API (`client.interactions.create`)

Identify which API features are used:
- [ ] Basic text generation
- [ ] System instructions
- [ ] Multi-turn conversation (chat or explicit history)
- [ ] Function calling / tools
- [ ] Structured output (JSON mode / response_schema)
- [ ] Multimodal (images, video, documents)
- [ ] Streaming
- [ ] Reasoning / thinking mode

Flag any features in the "cannot migrate" list and inform the user of alternatives before proceeding.

If the source model is a Gemini "pro" variant (`gemini-2.5-pro`, `gemini-3.1-pro-preview`), you **MUST** ask the user whether they have evaluated Nova 2 Lite for their use case.

### Step 2: Classify the Use Case

**Thinking/reasoning support by Gemini model:**

| Gemini Model | Native Thinking Support |
|--------------|------------------------|
| `gemini-2.0-flash` / `gemini-2.0-flash-lite` | No |
| `gemini-2.5-flash` / `gemini-2.5-pro` | Yes — `thinking_config` |
| `gemini-3.5-flash` / `gemini-3.1-pro-preview` | Yes — `thinking_config` |

**Migration rules for reasoning:**
- Source does NOT support thinking → omit `additionalModelRequestFields` entirely
- Source supports thinking but it's NOT enabled → omit `additionalModelRequestFields`
- Thinking IS enabled → ask the user which Nova effort level (see nova-target.md)

Then pick the Nova use-case type and inference config from **nova-target.md**.

### Step 3: Migrate the Code

You **MUST** load the `gemini-feature-mapping.md` steering file for the complete mapping table.
You **SHOULD** load the `gemini-code-examples.md` steering file for before/after patterns.

If the source uses the deprecated `google-generativeai` SDK or the Interactions API, also load the `gemini-generate-content-patterns.md` steering file for parameter mappings.

**SDK transformation:**
```python
# Gemini
from google import genai
client = genai.Client()
response = client.models.generate_content(model="gemini-3.5-flash", ...)

# Nova 2 Lite
import boto3
client = boto3.client("bedrock-runtime", region_name="us-east-1")
response = client.converse(modelId="us.amazon.nova-2-lite-v1:0", ...)
```

**Key transformations:**
- Remove `genai.configure(api_key=...)` — boto3 uses AWS credential chain
- `system_instruction="..."` → `system=[{"text": "..."}]`
- `contents=[{"role": "user", "parts": [...]}]` → `messages=[{"role": "user", "content": [{"text": "..."}]}]`
- `"role": "model"` → `"role": "assistant"`
- `generation_config={"temperature": T}` → `inferenceConfig={"temperature": T}`
- `max_output_tokens` → `maxTokens`
- `top_p` → `topP`
- `thinking_config=ThinkingConfig(...)` → `additionalModelRequestFields={"reasoningConfig": {...}}` (only when enabled)
- `previous_interaction_id` → pass full `messages` array

### Step 4: Migrate Structured Output

If the source uses `response_mime_type` + `response_schema`, apply this step.

- **Simple JSON (≤10 keys):** Inline schema in prompt + `temperature=0`
- **Complex JSON (>10 keys):** Tool-forcing with schema in `toolSpec.inputSchema`

### Step 5: Migrate Tool Calling

Key mappings:
- `function_declarations` → `toolSpec` (inside `toolConfig.tools`)
- `parameters` (OpenAPI schema) → `inputSchema.json` (JSON Schema — usually compatible)
- `tool_config.function_calling_config.mode` (`AUTO`/`ANY`/`NONE`) → `toolChoice` (`auto`/`any`/`tool`)
- Response `function_call` part → `toolUse` content block
- Send back `function_response` → `toolResult` content block

For deprecated SDK: `tools=[python_function]` (auto-extraction) → must write explicit tool schema.

### Step 6: Present the Result

```
## Migrated Code

**Source:** Gemini ({model name}) via {SDK variant}
**Use case:** {type}
**Inference config:** temperature={T}, reasoning={enabled/disabled}
**Breaking changes:** {list any features that couldn't be migrated 1:1}

### Code
{complete migrated code}

### Implementation Notes
- {inference config rationale}
- {any multimodal ordering requirements}
- {features requiring alternative approach}
- For prompt optimization, use the nova-prompter power
```

### Step 7: Validate

Run the validation checklist in the **nova-target.md** steering file, plus these Gemini-specific checks:
- [ ] No `google-genai` / `google-generativeai` imports remain
- [ ] No `genai.configure()` calls remain
- [ ] All `"role": "model"` changed to `"role": "assistant"`
- [ ] `previous_interaction_id` replaced with full message history
- [ ] `response_mime_type` / `response_schema` replaced with tool-forcing or inline schema
- [ ] `generation_config` / `GenerateContentConfig` fields mapped to `inferenceConfig` (camelCase)
- [ ] Multimodal: system prompt contains only persona; media precedes text

## Quick Reference

| Gemini | Nova 2 Lite |
|--------|-------------|
| `google-genai` / `google-generativeai` | `boto3` bedrock-runtime |
| `client.models.generate_content()` / `client.interactions.create()` | `client.converse()` |
| `system_instruction=` | `system=[{"text": "..."}]` |
| `contents=[{"role":"user","parts":[...]}]` | `messages=[{"role":"user","content":[{"text":"..."}]}]` |
| `generation_config={"temperature": T}` | `inferenceConfig={"temperature": T}` |
| `config=GenerateContentConfig(tools=[...])` | `toolConfig={"tools": [{toolSpec}]}` |
| `response_mime_type` + `response_schema` | Tool-forcing or inline prompt schema |
| `thinking_config=ThinkingConfig(...)` | `additionalModelRequestFields={"reasoningConfig": {...}}` |
| `client.models.generate_content_stream()` | `client.converse_stream()` |
| `"role": "model"` | `"role": "assistant"` |

## Common Mistakes

### Leaving `"role": "model"` in messages
**Problem:** Gemini uses `"model"` for assistant turns; Bedrock rejects it.
**Fix:** Change to `"role": "assistant"`.

### Passing `additionalModelRequestFields` when reasoning is disabled
**Problem:** Including reasoning config when the source didn't use thinking.
**Fix:** Omit `additionalModelRequestFields` entirely when reasoning is disabled.

### Using OpenAPI schema format for tools
**Problem:** Copying Gemini's tool parameter schemas without converting.
**Fix:** Ensure `inputSchema.json` uses JSON Schema format.

### Wrong media ordering
**Problem:** Putting text before images/video in the content array.
**Fix:** Media content blocks MUST come before the text block.

### Keeping `previous_interaction_id` pattern
**Problem:** Looking for a server-side state equivalent in Nova.
**Fix:** Nova has no server-side state — maintain and pass full `messages` array.
