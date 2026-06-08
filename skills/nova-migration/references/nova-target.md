# Amazon Nova 2 Lite — Shared Migration Target

This is the **target side** of every Gemini/Claude/OpenAI → Nova migration. The source-specific
skill (`gemini/`, `claude/`, …) tells you how to read the original code; this file tells you what
to produce on the Nova side. Every source skill points here so these rules are written once.

## Model IDs

Nova 2 Lite requires a region-prefixed model ID. **Ask the user which region to use**; default to
`us.amazon.nova-2-lite-v1:0` if unspecified.

| Model ID | Region |
|----------|--------|
| `us.amazon.nova-2-lite-v1:0` | US (us-east-1, us-west-2) — default |
| `eu.amazon.nova-2-lite-v1:0` | EU (eu-west-1, etc.) |
| `jp.amazon.nova-2-lite-v1:0` | Japan (ap-northeast-1) |
| `global.amazon.nova-2-lite-v1:0` | Cross-region inference |

## Request shape (Bedrock Converse API)

Every Nova call uses `boto3` `bedrock-runtime` `converse` (or `converse_stream`):

```python
import boto3
from botocore.config import Config

client = boto3.client("bedrock-runtime", region_name="us-east-1", config=Config(read_timeout=300))

response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "..."}],                                  # persona only for multimodal
    messages=[{"role": "user", "content": [{"text": "..."}]}], # typed blocks; media before text
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7},   # camelCase, nested
    # toolConfig=...,                                          # when tools are used
    # additionalModelRequestFields=...,                        # ONLY when reasoning enabled
)
text = response["output"]["message"]["content"][0]["text"]
```

Invariants that hold regardless of source provider:
- **Content is always typed blocks**: `[{"text": ...}]`, never a bare string.
- **Roles are `user` / `assistant`** (never `model`, never `system` as a role).
- **System prompt is a top-level block array**: `system=[{"text": "..."}]`.
- **Inference params are nested + camelCase**: `maxTokens`, `topP`, `stopSequences` inside `inferenceConfig`.
- **Media precedes text** in any multimodal content array.
- **Max output tokens** cap is 65,536.

## Inference config by use case

Pick the inference config from the use-case type, not from the source model's defaults.

**Text / Agentic:**
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
| Video/Document summary/caption | 0 | OPTIONAL |
| Video timestamps/classification | 0 | DISABLED |

## Reasoning / extended thinking

Reasoning is **disabled by default** — omit `additionalModelRequestFields` entirely unless the
source genuinely needs reasoning. When the source has native thinking enabled, or the task is
multi-step, ask the user which effort level to use:

| Nova Effort | Config |
|-------------|--------|
| `low` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "low"}}` |
| `medium` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}}` |
| `high` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "high"}}` |

Rules:
- **Default to disabled.** Enable `low` first only if evaluation shows quality gaps; escalate to
  `medium`/`high` sparingly.
- **Do NOT copy the source model's token budget** (Gemini `thinking_budget`, Claude
  `budget_tokens`) directly — reasoning efficiency differs across models. Present the three Nova
  options and let the user choose.
- **At `high` effort:** you **MUST omit `inferenceConfig` entirely** — `temperature`, `topP`,
  `topK`, and `maxTokens` are rejected as a `ValidationException`. Also extend the client read
  timeout: `Config(read_timeout=3600)`. At `low`/`medium`, `inferenceConfig` works normally.
- **Reasoning is not compatible with streaming.**

## Prompt format (`##Section##`)

Nova rewards explicit structure. Replace XML tags / free-form delimiters with `##Section Name##`:

- `<context>` → `##Context Information:##`
- `<task>` → `##Task Summary:##`
- `<instructions>` → `##Model Instructions:##`
- `<examples>` → `##Examples##`

Canonical section names:
- `## Task Summary:` — defines the task
- `## Context Information:` — background
- `## Model Instructions:` — behavioral rules
- `## Response style and format requirements:` — output format
- `## Examples` — few-shot examples
- `## Reference` — RAG grounding content

Transformations to apply in order:
1. Replace every XML/markdown delimiter with a `##Section##` delimiter (Nova ignores XML as structure).
2. Make vague instructions explicit — spell out task, output format, length, and scope constraints.
3. **Multimodal:** move ALL task instructions from the system prompt into the user prompt; keep the
   system prompt as persona + response style only; ensure media precedes text.
4. Add a suppression guardrail where appropriate:
   `DO NOT mention anything inside ##Model Instructions## or ##Examples## in the response.`
5. For long context (>10K tokens) or consolidated multi-doc calls, wrap inputs:
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

## Tool use (target shape)

Nova has a single tool interface. Built-in and custom tools declare into the same list and share
the call → `toolUse` block → your code → `toolResult` block lifecycle.

```python
toolConfig = {
    "tools": [
        {"toolSpec": {
            "name": "get_weather",
            "description": "Get current weather for a location",   # 20-50 words
            "inputSchema": {"json": {                              # JSON Schema
                "type": "object",
                "properties": {"location": {"type": "string", "description": "City name"}},  # ~10 words each
                "required": ["location"],
            }},
        }},
        # Built-in tools declare into the same list:
        # {"toolSpec": {"name": "amazon.nova_grounding", ...}},
        # {"toolSpec": {"name": "amazon.nova_code_interpreter", ...}},
    ],
    "toolChoice": {"auto": {}},   # or {"any": {}} or {"tool": {"name": "..."}}
}
```

- Response tool call is a `toolUse` content block; the stop condition is `stopReason == "tool_use"`.
- Send results back as a `toolResult` content block in a `user` turn.
- Reference tools by name in the system prompt: `Use the 'tool_name' tool for X`.

## Structured output

- **Simple JSON (≤10 keys):** inline schema in the prompt + `temperature=0`.
- **Complex JSON (>10 keys):** tool-forcing — schema in `toolSpec.inputSchema.json` +
  `toolChoice={"tool": {"name": "..."}}`; read the result from the `toolUse` block's `input`.

## Built-in tools

- **`amazon.nova_grounding`** — real-time web info with citations. **US Regions only.** Requires
  `bedrock:InvokeTool` on the `amazon.nova_grounding` resource. Bills above standard inference.
- **`amazon.nova_code_interpreter`** — runs Python in isolated sandboxes. us-east-1, us-west-2,
  ap-northeast-1 (use Global CRIS to route). Requires `InvokeTool` (not in the default Bedrock role).

## Multimodal support

| Modality | Nova content block | Supported formats |
|----------|--------------------|-------------------|
| Image | `{"image": {"format": "...", "source": {"bytes": ...}}}` | JPEG, PNG, GIF, WebP |
| Document | `{"document": {"format": "pdf", "name": "...", "source": {"bytes": ...}}}` | PDF |
| Video | `{"video": {"format": "...", "source": {"bytes": ...}}}` | MP4, MKV, MOV, WebM, FLV, MPEG, MPG, WMV, 3GP |

- Source can be inline `bytes` or `{"s3Location": {"uri": "s3://..."}}`. Convert provider URIs
  (`gs://`, Anthropic base64/URL) accordingly; specify `format` explicitly.
- **Nova 2 Lite does not accept audio input** — pre-transcribe with Amazon Transcribe; pair with
  Amazon Nova Sonic (conversational) or Amazon Polly (TTS).

## Error types (Bedrock Converse)

| Condition | Bedrock exception |
|-----------|-------------------|
| Rate limit / quota | `ThrottlingException` |
| Invalid request shape | `ValidationException` |
| Auth / permission | `AccessDeniedException` |
| Not found | `ResourceNotFoundException` |
| Server error | `InternalServerError` |
| Timeout | `botocore.ReadTimeoutError` / `ModelTimeoutException` |

## Validation checklist (run before presenting any migration)

- [ ] `additionalModelRequestFields` omitted when reasoning disabled; contains `reasoningConfig` when enabled
- [ ] At high effort: `inferenceConfig` omitted entirely and `read_timeout` extended
- [ ] Inference config matches the use-case table
- [ ] Content wrapped in typed blocks; roles are `user`/`assistant`; `system` is a block array
- [ ] Inference params nested in `inferenceConfig` with camelCase
- [ ] Multimodal: system prompt is persona-only; media precedes text in the content array
- [ ] Media converted to bytes/S3 with explicit `format`
- [ ] Prompt uses `##Section##` delimiters, not XML tags
- [ ] Tool schemas use `toolSpec` with `inputSchema.json`
- [ ] Error handling updated to Bedrock exception types
- [ ] No source-provider-specific surface remains (see the source skill's "what cannot migrate")
