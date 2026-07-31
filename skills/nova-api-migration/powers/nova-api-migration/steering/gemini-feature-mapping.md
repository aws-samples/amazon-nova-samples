# Gemini → Nova 2 Lite API Feature Mapping

## SDK & Client Initialization

| Gemini | Nova 2 Lite (Bedrock) |
|--------|----------------------|
| `from google import genai` | `import boto3` |
| `import google.generativeai as genai` | `import boto3` |
| `client = genai.Client()` | `client = boto3.client("bedrock-runtime", region_name="us-east-1")` |
| `genai.configure(api_key=...)` | Remove — boto3 uses AWS credential chain |
| `client.models.generate_content(...)` | `client.converse(...)` |
| `client.interactions.create(...)` | `client.converse(...)` |
| `model.generate_content(...)` (deprecated) | `client.converse(...)` |

## Model IDs

| Gemini Model | Nova Model ID |
|--------------|---------------------|
| `gemini-3.5-flash` | `us.amazon.nova-2-lite-v1:0` |
| `gemini-2.5-flash` | `us.amazon.nova-2-lite-v1:0` |
| `gemini-2.5-pro` / `gemini-3.1-pro-preview` | `us.amazon.nova-2-lite-v1:0` — **ask user to confirm** |
| `gemini-2.0-flash` / `gemini-2.0-flash-lite` | `us.amazon.nova-2-lite-v1:0` |

## System Instructions

| Gemini | Nova 2 Lite |
|--------|-------------|
| `system_instruction="..."` | `system=[{"text": "..."}]` |
| Persists across turns automatically | Re-specify each API call |
| Full instructions for all modalities | **Multimodal**: persona-only in system; task instructions in user message |

## Messages / Content

| Gemini | Nova 2 Lite |
|--------|-------------|
| `contents=[{"role": "user", "parts": [...]}]` | `messages=[{"role": "user", "content": [...]}]` |
| `Part(text="...")` | `{"text": "..."}` |
| `Part(inline_data={"mime_type": ..., "data": ...})` | `{"image": {"format": "png", "source": {"bytes": ...}}}` |
| `"role": "model"` | `"role": "assistant"` |
| Media can be anywhere in parts | Media MUST come before text in content array |
| `previous_interaction_id` | Pass full `messages` array |

## Generation Config → Inference Config

| Gemini | Nova 2 Lite |
|--------|-------------|
| `generation_config={"temperature": T}` | `inferenceConfig={"temperature": T}` |
| `config=GenerateContentConfig(temperature=T)` | `inferenceConfig={"temperature": T}` |
| `temperature` | `inferenceConfig.temperature` |
| `top_p` | `inferenceConfig.topP` |
| `top_k` | Not supported |
| `max_output_tokens` | `inferenceConfig.maxTokens` |
| `stop_sequences` | `inferenceConfig.stopSequences` |
| `candidate_count` | Not supported (always 1) |

## Function Calling / Tool Use

| Gemini | Nova 2 Lite |
|--------|-------------|
| `tools=[{"function_declarations": [...]}]` | `toolConfig={"tools": [{"toolSpec": {...}}]}` |
| `function_declarations.name` | `toolSpec.name` |
| `function_declarations.description` | `toolSpec.description` |
| `function_declarations.parameters` (OpenAPI) | `toolSpec.inputSchema.json` (JSON Schema) |
| `tool_config.function_calling_config.mode=AUTO` | `toolChoice={"auto": {}}` |
| `tool_config.function_calling_config.mode=ANY` | `toolChoice={"any": {}}` |
| `tool_config.function_calling_config.mode=NONE` | Remove `toolConfig` entirely |
| Response: `function_call` part | Response: `toolUse` content block |
| Send back: `function_response` part | Send back: `toolResult` content block |
| `tools=[python_function]` (auto-extract) | Must write explicit `toolSpec` schema |

## Structured Output

| Gemini | Nova 2 Lite |
|--------|-------------|
| `response_mime_type="application/json"` + `response_schema={...}` | No native JSON mode |
| Pydantic model / TypedDict as `response_schema` | Not supported |
| Simple schema (≤10 keys) | Inline schema in prompt + `temperature=0` |
| Complex schema (>10 keys) | Tool-forcing: `toolChoice={"tool":{"name":"..."}}` with schema in `inputSchema` |

## Reasoning / Thinking

| Gemini | Nova 2 Lite |
|--------|-------------|
| `thinking_config=ThinkingConfig(thinking_budget=N)` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "..."}}` |
| `ThinkingConfig(thinking_budget=0)` (disable) | Omit `additionalModelRequestFields` entirely |
| `ThinkingConfig(thinking_level="low"/"medium"/"high")` | Map to `maxReasoningEffort`: `"low"` / `"medium"` / `"high"` |
| Thought parts in response (`part.thought == True`) | `reasoningContent` blocks in response content |
| Default: disabled | Default: disabled — omit `additionalModelRequestFields` |

## Streaming

| Gemini | Nova 2 Lite |
|--------|-------------|
| `client.models.generate_content_stream(...)` | `client.converse_stream(...)` |
| `model.generate_content(..., stream=True)` (deprecated) | `client.converse_stream(...)` |
| `for chunk in response: chunk.text` | Event-based: `contentBlockDelta` → `delta.text` |

## Multimodal Content

| Gemini | Nova 2 Lite |
|--------|-------------|
| `Part.from_bytes(data=..., mime_type="image/png")` | `{"image": {"format": "png", "source": {"bytes": ...}}}` |
| `Part(inline_data={"mime_type":"video/mp4","data":...})` | `{"video": {"format": "mp4", "source": {"bytes": ...}}}` |
| File upload (`genai.upload_file(...)`) | Not available — pass bytes inline or S3 URI |
| No ordering constraint | Media MUST precede text |
| PIL.Image as input (deprecated SDK) | Read raw bytes |

## Response Parsing

| Gemini | Nova 2 Lite |
|--------|-------------|
| `response.text` | `response["output"]["message"]["content"][0]["text"]` |
| `response.candidates[0].content.parts` | `response["output"]["message"]["content"]` |
| `interaction.output_text` | `response["output"]["message"]["content"][0]["text"]` |
| `part.function_call` | `block["toolUse"]` |
| `response.usage_metadata` | `response["usage"]` |

## Features Without Direct Equivalent

| Gemini Feature | Nova Alternative |
|----------------|-----------------|
| `previous_interaction_id` (stateful) | Pass full message history |
| Managed agents / Antigravity | Build with tool use + orchestration |
| Deep Research agent | Not available |
| Google Search grounding | `amazon.nova_grounding` built-in tool |
| Code execution tool | `amazon.nova_code_interpreter` built-in tool |
| `store=true` (interaction persistence) | Manage state externally |
| Image generation | Amazon Nova Canvas (separate model) |
| Speech/TTS | Amazon Polly |
| `genai.upload_file(...)` | Pass bytes inline or S3 URI |
