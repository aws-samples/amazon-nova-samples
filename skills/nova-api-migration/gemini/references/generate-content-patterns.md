# Gemini API Migration Patterns

Covers the deprecated `google-generativeai` SDK and the Interactions API — patterns that need additional context beyond the main feature mapping.

## Deprecated SDK (`google-generativeai`)

### Detection
```python
import google.generativeai as genai
genai.configure(api_key="...")
model = genai.GenerativeModel("gemini-2.0-flash")
response = model.generate_content(...)
```

### Parameter Mapping

| Gemini (`google-generativeai`) | Nova 2 Lite (boto3) |
|-------------------------------|---------------------|
| `genai.configure(api_key=...)` | Remove — boto3 uses AWS credential chain |
| `genai.GenerativeModel(model_name)` | `modelId` param in `converse()` |
| `model.generate_content(prompt)` | `client.converse(messages=[...])` |
| `model.start_chat(history=[...])` | Pass full message history in `messages` |
| `chat.send_message(msg)` | Append to `messages` and call `converse()` again |
| `response.text` | `response["output"]["message"]["content"][0]["text"]` |

**GenerativeModel constructor params:**

| Gemini | Nova 2 Lite |
|--------|-------------|
| `model_name="gemini-2.0-flash"` | `modelId="us.amazon.nova-2-lite-v1:0"` |
| `system_instruction="..."` | `system=[{"text": "..."}]` |
| `generation_config={...}` | `inferenceConfig={...}` |
| `safety_settings=[...]` | No equivalent param — use guardrails in system prompt |
| `tools=[...]` | `toolConfig={"tools": [...]}` |
| `tools=[python_function]` (auto-extract) | Must write explicit `toolSpec` schema |

### Deprecated SDK Gotchas

| Pattern | Migration Notes |
|---------|----------------|
| `genai.configure(api_key=...)` | Remove entirely |
| `GenerativeModel(tools=[python_function])` | Must write explicit tool schema |
| `model.count_tokens(...)` | Not available in converse — estimate or use separate endpoint |
| `chat = model.start_chat()` | No chat object — maintain message list yourself |
| `response.prompt_feedback` | Not available — use CloudWatch metrics |
| `response.candidates[0].finish_reason` | `response["stopReason"]` |
| `PIL.Image` as input | Read raw bytes |
| `genai.upload_file(...)` | Pass bytes inline or use S3 URI |

---

## Interactions API

The Interactions API (`client.interactions.create`) is the newest Gemini pattern (google-genai >= 2.0). It provides server-side stateful multi-turn via `previous_interaction_id`.

### Parameter Mapping

| Gemini Interactions API | Nova 2 Lite (boto3 converse) |
|------------------------|------------------------------|
| `client.interactions.create(...)` | `client.converse(...)` |
| `model="gemini-3.5-flash"` | `modelId="us.amazon.nova-2-lite-v1:0"` |
| `input="..."` (string) | `messages=[{"role": "user", "content": [{"text": "..."}]}]` |
| `system_instruction="..."` | `system=[{"text": "..."}]` |
| `config=types.GenerateContentConfig(...)` | Split across `inferenceConfig`, `toolConfig`, `additionalModelRequestFields` |
| `config.temperature` | `inferenceConfig={"temperature": ...}` |
| `config.max_output_tokens` | `inferenceConfig={"maxTokens": ...}` |
| `config.tools` | `toolConfig={"tools": [...]}` |
| `config.thinking_config` | `additionalModelRequestFields={"reasoningConfig": {...}}` (only when enabled) |
| `previous_interaction_id=interaction.id` | Pass full `messages` array |
| `store=True` | Not available — manage state externally |
| `interaction.output_text` | `response["output"]["message"]["content"][0]["text"]` |
| `interaction.id` | No equivalent — track state in your application |

### Interactions API Gotchas

| Pattern | Migration Notes |
|---------|----------------|
| `previous_interaction_id` | No server-side state — maintain and pass full `messages` array |
| `interaction.steps` | `response["output"]["message"]["content"]` (list of content blocks) |
| `step.content[].function_call` | `block["toolUse"]` in content blocks |
| `store=True` | Not available — manage state externally |
