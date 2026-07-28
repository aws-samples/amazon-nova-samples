---
name: nova-api-migration-claude
description: Source guide for migrating Anthropic Claude Python API code to Amazon Nova 2 Lite. Covers the Anthropic Messages API (anthropic SDK) and Claude-on-Bedrock as source. Pairs with ../references/nova-target.md for the Nova side.
tags: [skill, migration, claude, anthropic, api, nova, bedrock]
---

# Claude → Nova 2 Lite (API Source Guide)

Covers the **Claude API source side**. For everything on the Nova side — model IDs, inference-config tables, reasoning effort rules, tool shape, structured output, streaming, and the validation checklist — read **`../references/nova-target.md`**. This file does not repeat them.

## Two Source Surfaces

You **MUST** identify which surface the customer is on first — the migration differs sharply:

1. **Anthropic Messages API** (`from anthropic import Anthropic`, `client.messages.create`) — calls `api.anthropic.com` with an API key. Full migration: SDK swap, auth change (API key → IAM), request/response reshaping.
2. **Claude on Bedrock** (`boto3` `converse` with a Claude `modelId`, or `AnthropicBedrock`) — already on Converse. Migration is much lighter: swap `modelId` to Nova, adjust reasoning config. No SDK or auth change.

> Most customers are on Bedrock already. Always check before assuming an SDK rewrite.

## Key API Differences (Anthropic Messages API → Nova)

1. **SDK**: `anthropic` → `boto3` Bedrock Runtime `converse`
2. **Auth**: Anthropic API key (`ANTHROPIC_API_KEY`) → AWS credentials (IAM)
3. **System prompt**: top-level `system` string/blocks → `system=[{"text": "..."}]`
4. **Message content**: string shorthand or `{"type":"text","text":"..."}` → typed blocks `{"text": ...}` (drop `type` key)
5. **Inference params**: top-level (`max_tokens`, `temperature`) → nested `inferenceConfig` (camelCase)
6. **Tools**: `tools=[{name, description, input_schema}]` → `toolConfig={"tools":[{"toolSpec":{...}}]}`
7. **Images**: base64 / URL → binary bytes / S3 + explicit `format`
8. **Extended thinking**: `thinking` blocks → `additionalModelRequestFields.reasoningConfig`
9. **Multimodal system prompt**: full instructions allowed → persona-only

> Roles are already `user`/`assistant` on both sides — no role rename needed.

### What Cannot Be Migrated Directly

- Audio input → Pre-transcribe with Amazon Transcribe; pair with Nova Sonic for voice
- Image generation → Use Amazon Nova Canvas
- Computer use / managed tool runtimes → Build with tool use + orchestration
- `cache_control` prompt-caching blocks → Bedrock prompt caching (different mechanism)
- Batch API → Use Bedrock batch inference

## Migration Workflow

Follow these steps in order. Confirm findings with the user after each step.

### Step 1: Analyze the Claude Code

Identify the source surface:
- [ ] **Anthropic Messages API** — `from anthropic import Anthropic`, `client.messages.create`, `AsyncAnthropic`
- [ ] **Claude on Bedrock** — `boto3` `converse` / `invoke_model` with `anthropic.claude-*` modelId, or `AnthropicBedrock`

Identify features used:
- [ ] Basic text generation
- [ ] System prompt
- [ ] Multi-turn conversation
- [ ] Tool use
- [ ] Structured output (tool-forcing)
- [ ] Multimodal (images, documents)
- [ ] Streaming
- [ ] Extended thinking / CoT

Flag any "cannot migrate" features and offer alternatives before proceeding.

**Source model expectations:**

| Source Claude Model | Note |
|---|---|
| Claude 3 Haiku | Direct replacement for most workloads |
| Claude 3.5 Haiku | Benchmark parity; Nova adds video input |
| Claude Haiku 4.5 | Confirm the quality gap justifies higher cost |
| Claude 3 Sonnet / 3.5 Sonnet | **Ask user to confirm** they have evaluated Nova 2 Lite |

### Step 2: Classify the Use Case

**Native thinking support:**
- Claude 3 / 3.5 Haiku: **NO** native thinking. Any reasoning is prompt-based CoT.
- Claude 3.5 Sonnet / Haiku 4.5: YES — `thinking={"type":"enabled","budget_tokens":N}`

**Migration rules:**
- CoT prompting only (no `thinking`) → reasoning **disabled**; keep CoT text in prompt
- `thinking` enabled → enable Nova reasoning and ask which effort level (see nova-target.md). Do NOT copy `budget_tokens` directly.
- Default: start disabled; enable `low` only if evaluation shows gaps

Then pick the Nova use-case type and inference config from **nova-target.md**.

### Step 3: Migrate the Code

You **MUST** read `references/feature-mapping.md` for the complete mapping table.
You **SHOULD** read `references/code-examples.md` for before/after patterns.

**SDK transformation — Anthropic Messages API source:**
```python
# Claude
from anthropic import Anthropic
client = Anthropic(api_key="...")
response = client.messages.create(
    model="claude-3-5-haiku-20241022",
    max_tokens=1024,
    system="You are a helpful assistant.",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.7,
)
print(response.content[0].text)

# Nova 2 Lite
import boto3
from botocore.config import Config
client = boto3.client("bedrock-runtime", region_name="us-east-1", config=Config(read_timeout=300))
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a helpful assistant."}],
    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
)
print(response["output"]["message"]["content"][0]["text"])
```

**Key transformations:**
- Remove `Anthropic(api_key=...)` — boto3 uses AWS credential chain
- `system="..."` (string) → `system=[{"text": "..."}]`
- `system=[{"type":"text","text":"..."}]` → `system=[{"text": "..."}]` (drop `type`)
- Message content string shorthand → typed blocks: `"content": "text"` → `"content": [{"text": "text"}]`
- `max_tokens` → `inferenceConfig.maxTokens`
- `temperature` → `inferenceConfig.temperature`
- `top_p` → `inferenceConfig.topP`
- `stop_sequences` → `inferenceConfig.stopSequences`
- `response.content[0].text` → `response["output"]["message"]["content"][0]["text"]`
- `thinking={"type":"enabled","budget_tokens":N}` → `additionalModelRequestFields={"reasoningConfig": {...}}` (only when enabled)

**Claude-on-Bedrock source (light path):**
```python
# Before: Claude on Bedrock
response = client.converse(
    modelId="anthropic.claude-3-5-haiku-20241022-v1:0",
    system=[{"text": "You are a helpful assistant."}],
    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
)

# After: Nova 2 Lite — just swap modelId (+ reasoning config if applicable)
response = client.converse(
    modelId="us.amazon.nova-2-lite-v1:0",
    system=[{"text": "You are a helpful assistant."}],
    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
)
```

### Step 4: Migrate Structured Output

Claude tool-forcing (`tool_choice={"type":"tool","name":"..."}`) maps to Nova `toolChoice={"tool":{"name":"..."}}`. For simple schemas (≤10 keys), inline-prompt variant is lighter.

### Step 5: Migrate Tool Calling

Key mappings:
- `tools=[{"name", "description", "input_schema": {...}}]` → `toolConfig={"tools":[{"toolSpec":{"name", "description", "inputSchema":{"json":{...}}}}]}`
- `input_schema` (JSON Schema) → `inputSchema.json` (usually a 1:1 lift)
- `tool_choice` (`auto`/`any`/`tool`) → `toolChoice` (same semantics, different shape)
- Response `tool_use` block → `toolUse` content block
- `tool_result` → `toolResult` content block
- `stop_reason == "tool_use"` → `stopReason == "tool_use"`

**`tool_choice` mapping:**

| Claude `tool_choice` | Nova `toolChoice` |
|---------------------|-------------------|
| `{"type": "auto"}` | `{"auto": {}}` |
| `{"type": "any"}` | `{"any": {}}` |
| `{"type": "tool", "name": "X"}` | `{"tool": {"name": "X"}}` |

### Step 6: Present the Result

```
## Migrated Code

**Source:** Claude ({model name}) via {Anthropic API / Bedrock}
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

Run the **nova-target.md validation checklist**, plus these Claude-specific checks:
- [ ] No `anthropic` imports remain (for Anthropic API source)
- [ ] No `ANTHROPIC_API_KEY` / `Anthropic(...)` / `AnthropicBedrock(...)` client remains
- [ ] `system` converted from string/typed-blocks to `[{"text": ...}]`
- [ ] Message content wrapped in blocks (no string shorthand)
- [ ] Inference params nested in `inferenceConfig` (not top-level)
- [ ] Images converted from base64 to bytes with explicit `format`
- [ ] `cache_control` blocks removed (use Bedrock prompt caching separately if needed)
- [ ] `thinking` config replaced with `reasoningConfig` in `additionalModelRequestFields`
- [ ] For Bedrock source: `modelId` swapped, reasoning config adjusted — nothing else changed

## Quick Reference

| Claude (Anthropic Messages API) | Nova 2 Lite |
|--------|-------------|
| `anthropic` SDK | `boto3` bedrock-runtime |
| `client.messages.create()` | `client.converse()` |
| `system="..."` (string/blocks) | `system=[{"text": "..."}]` |
| `max_tokens`, `temperature` (top-level) | `inferenceConfig={"maxTokens": ..., "temperature": ...}` |
| `tools=[{name, description, input_schema}]` | `toolConfig={"tools":[{"toolSpec":{...}}]}` |
| `tool_choice` | `toolChoice` |
| image base64 `{"type":"image","source":{...}}` | `{"image":{"format":"jpeg","source":{"bytes":...}}}` |
| `thinking={"budget_tokens": N}` | `additionalModelRequestFields={"reasoningConfig": {...}}` |
| `client.messages.stream()` / `stream=True` | `client.converse_stream()` |
| `response.content[0].text` | `response["output"]["message"]["content"][0]["text"]` |

## Common Mistakes

### Assuming an SDK rewrite when already on Bedrock
**Problem:** Rewriting the entire client setup when the source is already `boto3` `converse` with a Claude modelId.
**Fix:** Detect the surface first; the Bedrock path is just modelId + reasoning-config.

### Inference params at top level
**Problem:** Passing `max_tokens`/`temperature` as top-level converse args.
**Fix:** Nest in `inferenceConfig` (camelCase).

### Images left as base64
**Problem:** Passing Anthropic-style base64 image data directly.
**Fix:** Decode to raw bytes, pass with explicit `format`, and place before text in content array.

### `inferenceConfig` left in at high reasoning effort
**Problem:** Bedrock rejects temperature/topP/topK/maxTokens with high effort.
**Fix:** Omit `inferenceConfig` entirely at high effort; set `read_timeout=3600`.

### Content string shorthand not converted
**Problem:** Passing `"content": "hello"` (Claude allows string shorthand, Bedrock does not).
**Fix:** Wrap as `"content": [{"text": "hello"}]`.
