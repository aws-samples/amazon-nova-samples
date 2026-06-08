---
name: nova-migration-claude
description: Source guide for migrating Anthropic Claude Python code and prompts to Amazon Nova 2 Lite. Read after nova-migration routes a Claude source here. Handles both the Anthropic Messages API (anthropic SDK) and Claude-on-Bedrock as source, with the full Claude→Nova feature mapping. Pairs with ../references/nova-target.md for the Nova side.
tags: [skill, migration, claude, anthropic, nova, bedrock]
---

# Claude → Nova 2 Lite (source guide)

Covers the **Claude source side**. For everything on the Nova side — model IDs, inference-config
tables, reasoning effort rules, `##Section##` prompt format, tool shape, structured output, and the
validation checklist — read **`../references/nova-target.md`**. This file does not repeat them.

## Two source surfaces

You **MUST** identify which surface the customer is on first — the migration differs sharply:

1. **Anthropic Messages API** (`from anthropic import Anthropic`, `client.messages.create`) — calls
   `api.anthropic.com` with an API key. Full migration: SDK swap, auth change (API key → IAM),
   request/response reshaping.
2. **Claude on Bedrock** (`boto3` `converse` with a Claude `modelId`, or `AnthropicBedrock`) —
   already on Converse. Migration is much lighter: swap `modelId` to Nova, move any reasoning
   config to `additionalModelRequestFields`, and reformat the prompt. No SDK or auth change.

> Most customers are on Bedrock already. Always check before assuming an SDK rewrite.

## Claude-side key differences (Anthropic Messages API → Nova)

1. **SDK**: `anthropic` → `boto3` Bedrock Runtime `converse`
2. **Auth**: Anthropic API key → AWS credentials (IAM)
3. **System prompt**: top-level `system` string/blocks → `system=[{"text": "..."}]`
4. **Message content**: string shorthand or `{"type":"text",...}` → typed blocks `{"text": ...}`
5. **Inference params**: top-level (`max_tokens`, `temperature`) → nested `inferenceConfig` (camelCase)
6. **Tools**: `tools=[{type, function:{...}}]` → `toolConfig={"tools":[{"toolSpec":{...}}]}`
7. **Images**: base64 / URL → binary bytes / S3 + explicit `format`
8. **Prompt format**: XML tags / free-form → `##Section Name##`
9. **Extended thinking**: Claude `thinking` blocks / CoT → `additionalModelRequestFields.reasoningConfig`
10. **Multimodal system prompt**: full instructions allowed → persona-only

> Roles are already `user`/`assistant` on both sides — no role rename (unlike Gemini's `model`).

### What cannot be migrated directly

- Audio input → Nova does not accept audio. Pre-transcribe with Amazon Transcribe; pair with Nova
  Sonic (conversational) or Amazon Polly (TTS)
- Image generation → Amazon Nova Canvas
- Computer use / managed tool runtimes → build with tool use + orchestration (e.g., AgentCore)
- `cache_control` prompt-caching blocks → Bedrock prompt caching (different surface)

## Workflow

Follow in order; confirm findings with the user after each step.

### Step 1: Analyze the Claude code

Identify the source surface (see above):
- [ ] Anthropic Messages API — `from anthropic import Anthropic`, `client.messages.create`, `AsyncAnthropic`, `AnthropicBedrock`
- [ ] Claude on Bedrock — `boto3` `converse` / `invoke_model` with `anthropic.claude-*`

Identify features used: basic text, system prompt, multi-turn, tool use, structured output,
multimodal, streaming, extended thinking / CoT, prompt caching.

Flag any "cannot migrate" features and offer the alternative before proceeding.

Source model expectations:

| Source Claude model | Complexity | Note |
|---|---|---|
| Claude 3 Haiku | Low | Direct replacement for most workloads |
| Claude 3.5 Haiku | Low–Medium | Benchmark parity; Nova adds video input |
| Claude Haiku 4.5 | High | Marginal edge over Nova Lite; confirm the quality gap is worth the higher cost |
| Claude 3 Sonnet | Medium | Validate with task benchmarks; consider medium reasoning |
| Claude 3.5 Sonnet | Medium–High | Test aggressively before committing |

If the source is **Sonnet/Opus-tier**, you **MUST** ask whether the user has evaluated Nova 2 Lite
for their use case — higher-tier Claude models have higher capability ceilings.

### Step 2: Classify the use case

**Native thinking:** Claude 3 / 3.5 Haiku have **none** (any reasoning is prompt-based CoT). Claude
3.5 Sonnet and Haiku 4.5 support `thinking={"type":"enabled","budget_tokens":N}`.

Thinking migration rules:
- CoT prompting only (no `thinking`) → reasoning **disabled**; keep the CoT text.
- `thinking` enabled, or task is genuinely multi-step → enable Nova reasoning and ask which effort
  level (see nova-target "Reasoning"). Do NOT copy Claude's `budget_tokens` directly.
- **Default rule:** start with reasoning disabled; enable `low` only if evaluation shows gaps; for
  latency-sensitive endpoints stay disabled or `low`.

Then pick the Nova use-case type and inference config from **nova-target.md**.

### Step 3: Migrate the code

You **MUST** read `references/feature-mapping.md` for the complete Claude→Nova mapping table.
You **SHOULD** read `references/code-examples.md` for before/after patterns (both source surfaces,
including the light Claude-on-Bedrock path — Example 5).

If the source uses the Anthropic Messages API or `AnthropicBedrock`, you **MUST** also read
`references/messages-api-patterns.md` for parameter mappings, streaming/multi-turn/tool-loop
reshaping, and async-client handling.

Ask which region model ID to use (default `us.amazon.nova-2-lite-v1:0`) — see nova-target.

**SDK transformation — Anthropic Messages API source:**
```python
# Claude
from anthropic import Anthropic
client = Anthropic(api_key="...")
resp = client.messages.create(model="claude-3-5-haiku-...", max_tokens=1024, system="...", messages=[...])

# Nova 2 Lite
import boto3
from botocore.config import Config
client = boto3.client("bedrock-runtime", region_name="us-east-1", config=Config(read_timeout=300))
resp = client.converse(modelId="us.amazon.nova-2-lite-v1:0", system=[{"text": "..."}], messages=[...], inferenceConfig={"maxTokens": 1024})
```

**Claude-on-Bedrock source (light path):** swap `modelId` to Nova, reformat the prompt, and map any
`thinking` config to `reasoningConfig`. No SDK or auth change.

Include `additionalModelRequestFields` ONLY when reasoning is enabled (see nova-target).

### Step 4: Migrate the prompt

Apply the `##Section##` transformations from **nova-target.md → "Prompt format"**. Claude-specific
note: Claude prompts lean heavily on XML tags (`<document>`, `<thinking>`, `<instructions>`) —
convert **every** tag to a `##Section##` delimiter, and make implicit instructions explicit.

### Step 5: Structured output

Claude tool-forcing (`tool_choice={"type":"tool",...}`) maps directly to Nova
`toolChoice={"tool":{"name":...}}`. For simple schemas, the inline-prompt variant is lighter. See
nova-target "Structured output" and `references/code-examples.md` Example 3.

### Step 6: Tool calling

Claude → Nova specifics (target shape is in nova-target "Tool use"):
- `tools=[{name, description, input_schema}]` → `toolConfig={"tools":[{"toolSpec":{..., "inputSchema":{"json":{...}}}}]}`
- `input_schema` (JSON Schema) → `inputSchema.json` (usually a 1:1 lift)
- `tool_choice` (`auto`/`any`/`tool`) → `toolChoice`
- Response `tool_use` block / `stop_reason == "tool_use"` → `toolUse` / `stopReason == "tool_use"`
- `tool_result` → `toolResult` content block

### Step 7: Present the result

Use the output format in **nova-target.md**, and add a **Source surface** line
(Anthropic Messages API | Claude on Bedrock).

### Step 8: Validate

Run the **nova-target.md validation checklist**, plus these Claude-specific checks:
- [ ] Anthropic source: `system` → `[{"text": ...}]`; content wrapped in typed blocks; params nested in `inferenceConfig`
- [ ] Images converted from base64/URL to bytes/S3 with explicit `format`
- [ ] No Anthropic-specific surface remains (`messages.create`, `cache_control`, `x-api-key`)

## Quick reference

| Claude (Anthropic Messages API) | Nova 2 Lite |
|--------|-------------|
| `anthropic` SDK | `boto3` bedrock-runtime |
| `client.messages.create()` | `client.converse()` |
| `system="..."` (string/blocks) | `system=[{"text": "..."}]` |
| `max_tokens`, `temperature` (top-level) | `inferenceConfig={"maxTokens": ..., "temperature": ...}` |
| `tools=[{function:{...}}]` | `toolConfig={"tools":[{"toolSpec":{...}}]}` |
| `tool_choice` | `toolChoice` |
| image base64 `{"type":"image","source":{...}}` | `{"image":{"format":"jpeg","source":{"bytes":...}}}` |
| `thinking={"budget_tokens": N}` / CoT | `additionalModelRequestFields={"reasoningConfig": {...}}` |
| `stream=True` / `messages.stream()` | `client.converse_stream()` |
| XML tags in prompt | `##Section Name##` delimiters |

## Common mistakes

- **Assuming an SDK rewrite when already on Bedrock** — detect the surface first; the Bedrock path is just modelId + prompt + reasoning-config.
- **XML tags left in the prompt** — Claude leans on them; Nova ignores them. Convert to `##Section##`.
- **Inference params at top level** — nest in `inferenceConfig` (camelCase) or Bedrock rejects them.
- **Full system instructions in multimodal calls** — move everything except persona to the user prompt; media before text.
- **Images left as base64** — convert to bytes/S3 with explicit `format`.
- **`inferenceConfig` left in at high reasoning effort** — omit it entirely; also set `read_timeout=3600`.
