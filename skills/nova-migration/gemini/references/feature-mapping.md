# Gemini to Nova 2 Lite Feature Mapping

## SDK & Client Initialization

| Gemini | Nova 2 Lite (Bedrock) |
|--------|----------------------|
| `from google import genai` | `import boto3` |
| `client = genai.Client()` | `client = boto3.client("bedrock-runtime")` |
| `client.models.generate_content(...)` | `client.converse(...)` |
| `client.interactions.create(...)` | `client.converse(...)` |
| API key auth (`GOOGLE_API_KEY`) | AWS credentials (IAM role, profile, or env vars) |

## Model IDs

Nova 2 Lite requires a region-prefixed model ID. Ask the user which region to use:

| Model ID | Region |
|----------|--------|
| `us.amazon.nova-2-lite-v1:0` | US (default) |
| `eu.amazon.nova-2-lite-v1:0` | EU |
| `jp.amazon.nova-2-lite-v1:0` | Japan |
| `global.amazon.nova-2-lite-v1:0` | Cross-region |

**Gemini → Nova mapping (default US):**

| Gemini Model | Nova Model ID |
|--------------|---------------------|
| `gemini-3.5-flash` | `us.amazon.nova-2-lite-v1:0` |
| `gemini-2.5-flash` | `us.amazon.nova-2-lite-v1:0` |
| `gemini-2.5-pro` / `gemini-3.1-pro-preview` | `us.amazon.nova-2-lite-v1:0` — **ask user to confirm they have evaluated Nova 2 Lite for their use case before proceeding** |
| `gemini-2.0-flash` | `us.amazon.nova-2-lite-v1:0` |
| `gemini-2.0-flash-lite` | `us.amazon.nova-2-lite-v1:0` |

## System Instructions

| Gemini | Nova 2 Lite |
|--------|-------------|
| `system_instruction="..."` param | `system` field in converse API with `text` content blocks |
| Full instructions allowed for all modalities | **MULTIMODAL RESTRICTION**: System prompt limited to persona + response style only. All task instructions MUST go in user message. |
| Persists across turns automatically | Re-specify each API call |

## Interactions API

The Interactions API (`client.interactions.create`) is the newest Gemini API pattern (google-genai >= 2.0). It provides a simplified interface with server-side stateful multi-turn.

| Gemini (Interactions API) | Nova 2 Lite (Bedrock) |
|--------------------------|----------------------|
| `client.interactions.create(model=..., input=...)` | `client.converse(modelId=..., messages=[...])` |
| `input="..."` (string) | `messages=[{"role": "user", "content": [{"text": "..."}]}]` |
| `system_instruction="..."` (direct param) | `system=[{"text": "..."}]` |
| `config=types.GenerateContentConfig(...)` | Split across `inferenceConfig`, `toolConfig`, `additionalModelRequestFields` |
| `previous_interaction_id=interaction.id` | Pass full `messages` array with conversation history |
| `store=True` (persist interaction server-side) | Not available — manage state externally |
| `interaction.output_text` | `response["output"]["message"]["content"][0]["text"]` |
| `interaction.steps` (list of ThoughtStep/ModelOutputStep) | `response["output"]["message"]["content"]` (list of content blocks) |
| `step.content[].function_call` (on ModelOutputStep) | `block["toolUse"]` in content blocks |
| `interaction.id` (for chaining turns) | No equivalent — track conversation state in application |

## Messages / Content

| Gemini | Nova 2 Lite |
|--------|-------------|
| `contents=[{"role": "user", "parts": [...]}]` | `messages=[{"role": "user", "content": [...]}]` |
| `Part(text="...")` | `{"text": "..."}` |
| `Part(inline_data={"mime_type": ..., "data": ...})` | `{"image": {"format": "png", "source": {"bytes": ...}}}` |
| Media can be anywhere in parts | Media MUST come before text in content array |
| `previous_interaction_id` for multi-turn | Pass full `messages` array with conversation history |

## Function Calling / Tool Use

| Gemini | Nova 2 Lite |
|--------|-------------|
| `tools=[{"function_declarations": [...]}]` | `toolConfig={"tools": [{"toolSpec": {...}}]}` |
| `function_declarations.name` | `toolSpec.name` |
| `function_declarations.description` | `toolSpec.description` |
| `function_declarations.parameters` (OpenAPI schema) | `toolSpec.inputSchema.json` (JSON Schema) |
| `tool_config.function_calling_config.mode` = `AUTO`/`ANY`/`NONE` | `toolChoice`: `auto` / `any` / `tool` (force specific) |
| Response: `function_call` part | Response: `toolUse` content block |
| Send back: `function_response` part | Send back: `toolResult` content block |

## Structured Output

| Gemini | Nova 2 Lite |
|--------|-------------|
| `config=GenerateContentConfig(response_mime_type="application/json", response_schema={...})` | No native JSON mode — use tool-forcing for complex schemas (>10 keys) or inline schema in prompt for simple JSON |
| Can also pass Pydantic model or TypedDict as `response_schema` | Prompt: `"You MUST answer in JSON format only"` + `temperature=0` |
| Schema enforced natively | Schema enforced via `toolChoice: {tool: {name: ...}}` with schema in `inputSchema` |

## Reasoning / Thinking

**Which Gemini models support thinking:**
- `gemini-2.0-flash` / `gemini-2.0-flash-lite`: NO native thinking. Any reasoning is prompt-based CoT.
- `gemini-2.5-flash` / `gemini-2.5-pro` / `gemini-3.5-flash` / `gemini-3.1-pro-preview`: YES — uses `thinking_config=types.ThinkingConfig(...)`.

| Gemini | Nova 2 Lite |
|--------|-------------|
| `config=types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_budget=N))` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}}` |
| `types.ThinkingConfig(thinking_budget=0)` (disable) | Omit `additionalModelRequestFields` entirely |
| `types.ThinkingConfig(thinking_level="low"/"medium"/"high")` (alternative) | Map to Nova `maxReasoningEffort`: `"low"` / `"medium"` / `"high"` |
| Thought parts in response (`part.thought == True`) | `reasoningContent` blocks in response content |
| Can combine with any feature | Cannot combine with assistant prefill |
| Default: disabled | Default: disabled — omit `additionalModelRequestFields` |

**Effort translation — ask the user:**

Do NOT copy Gemini's `budget_tokens` value directly — the models have different reasoning efficiency. Present these Nova options and let the user choose:

| Nova Effort | Config |
|-------------|--------|
| `low` | `{"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "low"}}` |
| `medium` | `{"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}}` |
| `high` | `{"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "high"}}` — **MUST omit `inferenceConfig`** entirely |

## Generation Config / Inference Config

| Gemini | Nova 2 Lite |
|--------|-------------|
| `generation_config={"temperature": 0.7, "top_p": 0.9, "max_output_tokens": 1024}` | `inferenceConfig={"temperature": 0.7, "topP": 0.9, "maxTokens": 1024}` |
| `stop_sequences=["..."]` | `inferenceConfig.stopSequences=["..."]` |
| `candidate_count` | Not supported (always 1) |
| `top_k` | Not directly supported |

## Streaming

| Gemini | Nova 2 Lite |
|--------|-------------|
| `client.models.generate_content_stream(...)` separate method | `client.converse_stream(...)` separate method |
| Iterate chunks: `for chunk in response: chunk.text` | Event types: `contentBlockStart`, `contentBlockDelta`, `contentBlockStop`, `messageStop` |
| `chunk.text` | `event["contentBlockDelta"]["delta"]["text"]` |

## Multimodal Content

| Gemini | Nova 2 Lite |
|--------|-------------|
| Images via `Part(inline_data=...)` or file URI | Images via `{"image": {"format": "...", "source": {"bytes": ...}}}` |
| Video via file upload | Video via `{"video": {"format": "...", "source": {"bytes": ...}}}` |
| Documents via file upload | Documents via `{"document": {"format": "pdf", "name": "...", "source": {"bytes": ...}}}` |
| Supports: JPEG, PNG, GIF, WebP, PDF, MP4, etc. | Supports: JPEG, PNG, GIF, WebP (images); PDF (documents); MP4, MKV, MOV, WebM, FLV, MPEG, MPG, WMV, 3GP (video) |
| No ordering constraint | Media MUST precede text in content array |
| System instructions work normally | System prompt restricted to persona only |

## Prompt Structure

| Gemini | Nova 2 Lite |
|--------|-------------|
| XML tags, markdown, free-form | `##Section Name##` delimiters (NOT XML tags) |
| `<context>...</context>` | `##Context Information:##` |
| `<task>...</task>` | `##Task Summary:##` |
| `<instructions>...</instructions>` | `##Model Instructions:##` |
| Free-form section naming | Canonical section names required (see nova2-prompt skill) |

## Features Without Direct Equivalent

| Gemini Feature | Nova 2 Lite Alternative |
|----------------|------------------------|
| `previous_interaction_id` (stateful) | Pass full message history |
| Managed agents / Antigravity | Not available — build with tool use + orchestration |
| Deep Research agent | Not available |
| Google Search grounding | Nova Web Grounding (built-in tool) |
| Code execution tool | Not built-in — use tool calling with custom code executor |
| `store=true` (interaction persistence) | Not available — manage state externally |
| Image generation | Not available in Nova Lite — use Amazon Nova Canvas |
| Speech/TTS generation | Not available in Nova Lite — use Amazon Polly |
