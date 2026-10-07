# OpenAI → Nova 2 Lite Migration Skill

An [Agent Skill](https://agentskills.io/specification) that migrates OpenAI Python code and prompts to [Amazon Nova 2 Lite](https://docs.aws.amazon.com/nova/latest/nova2-userguide/getting-started-nova-2.html) (`us.amazon.nova-2-lite-v1:0`) on Amazon Bedrock.

The skill converts SDK calls (`openai` → `boto3` Bedrock Runtime `converse`) and rewrites prompts to follow Nova 2 Lite formatting and constraints. This is not a one-line model swap — authentication, message structure, parameter nesting, and error handling all change. Every migration delivers two things: **working migrated code** and an **explanation of every change**, including any features that can't be ported 1:1.

The skill supports two source situations:

1. **OpenAI API** (`api.openai.com`) — GPT-4o, GPT-4.1, GPT-5.x, and legacy GPT-4 / GPT-3.5, across the Chat Completions, Responses, and Assistants API styles.
2. **OpenAI on Amazon Bedrock** — OpenAI models already hosted on Bedrock (GPT-5.5 / GPT-5.4 via the Responses API, and gpt-oss-120b / 20b via Converse / Responses / Chat Completions), common when swapping a model in a multi-model Bedrock bake-off. Auth/Region/billing are already AWS-native, so this path is usually lower-effort.

| Source | Detected from |
|---|---|
| OpenAI API — Chat Completions | `client.chat.completions.create(...)` |
| OpenAI API — Responses | `client.responses.create(...)` |
| OpenAI API — Assistants | `client.beta.assistants.create(...)` / `client.beta.threads.*` |
| OpenAI on Bedrock — Responses | `openai`/`BedrockOpenAI` client on a `bedrock-mantle` base URL, `openai.gpt-5.5` / `openai.gpt-5.4` |
| OpenAI on Bedrock — Converse/other | `boto3` `converse`/`invoke_model` with an `openai.gpt-oss-*` model ID |

**Target:** `us.amazon.nova-2-lite-v1:0`

## Skill structure

```
openai-to-nova-migration/
├── SKILL.md                              # Skill instructions and migration workflow
├── README.md                             # This file
└── references/
    ├── feature-mapping.md                # Complete OpenAI → Nova mapping tables
    ├── code-examples.md                  # Before/after code patterns
    ├── chat-completions-patterns.md      # Chat Completions, Responses API + Assistants API specifics
    └── openai-on-bedrock-patterns.md     # OpenAI models hosted on Bedrock (GPT-5.5/5.4, gpt-oss) → Nova
```

## What the skill handles

| Area | Detail |
|---|---|
| SDK | `openai` → `boto3` bedrock-runtime `converse` / `converse_stream` |
| Auth | `OPENAI_API_KEY` (bearer token) → AWS IAM credentials |
| Request structure | `role: "system"` message → `system=[{"text": ...}]`; flat string content → typed content blocks |
| Inference params | Top-level `max_tokens`/`temperature`/`top_p` → nested `inferenceConfig` with camelCase |
| Prompt format | Free-form → `##Section Name##` delimiters with canonical Nova section names |
| Multimodal | Enforces system-prompt-is-persona-only rule, media-before-text ordering, URL/base64 → raw bytes |
| Function calling | `tools` (function) → `toolSpec`, `tool_choice` → `toolChoice` |
| Structured output | `response_format` → inline schema (simple) or tool-forcing (complex) |
| Reasoning | `reasoning_effort` (GPT-5.x) → `additionalModelRequestFields.reasoningConfig`, mapped to a Nova effort level |
| Built-in tools | Assistants code interpreter / file search → Nova `nova_code_interpreter` / Bedrock Knowledge Bases |
| Error handling | `RateLimitError` / `APIError` → `ThrottlingException` / `ValidationException` |

## API differences at a glance

| | OpenAI | Nova 2 Lite |
|---|---|---|
| **SDK** | `openai` | `boto3` bedrock-runtime |
| **Call** | `client.chat.completions.create()` / `client.responses.create()` | `client.converse()` |
| **Auth** | `OPENAI_API_KEY` | AWS credentials (IAM role, profile, env vars) |
| **System prompt** | `{"role": "system", ...}` message | `system=[{"text": ...}]` (persona only for multimodal) |
| **Message content** | Flat string | Typed content blocks (`[{"text": ...}]`) |
| **Inference params** | Top-level `max_tokens`, `temperature`, `top_p` | Nested `inferenceConfig` (`maxTokens`, `temperature`, `topP`) |
| **Tools** | `tools=[{"type": "function", ...}]` | `toolConfig={"tools": [{"toolSpec": ...}]}` |
| **Tool choice** | `tool_choice` (`auto`/`required`/`none`) | `toolChoice` (`auto`/`any`/`tool`) |
| **Structured output** | `response_format` (JSON schema) | Inline prompt schema or tool-forcing |
| **Reasoning** | `reasoning_effort` (GPT-5.x) | `additionalModelRequestFields={"reasoningConfig": {...}}` |
| **Streaming** | `stream=True` | `converse_stream()` |
| **Stateful turns** | Assistants threads, `previous_response_id` | Pass full message history each call |
| **Images** | URL or base64 data URI | Raw binary bytes; media MUST precede text |
| **Errors** | `RateLimitError` / `APIError` | `ThrottlingException` / `ValidationException` |

## Reasoning effort mapping

When the source model supports reasoning effort (GPT-5.x, `o1`, `o3`) **and** it's enabled, the skill asks the user which Nova effort level to use:

| Nova effort | Config |
|---|---|
| `low` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "low"}}` |
| `medium` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}}` |
| `high` | `additionalModelRequestFields={"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "high"}}` — must omit `inferenceConfig` and set client `read_timeout=3600` |

OpenAI and Nova effort scales are not numerically equivalent — start at Nova `low` and increase only if evaluation shows quality gaps. If the source model has no native reasoning (e.g. `gpt-4o`), or `reasoning_effort` isn't enabled, omit `additionalModelRequestFields` entirely (reasoning is disabled by default).

## Installation

### Claude Code

This skill ships as the `openai-to-nova-migration` plugin via the `aws-samples-amazon-nova-samples` marketplace.

Add the marketplace, then install the plugin:

```
/plugin marketplace add https://github.com/aws-samples/amazon-nova-samples
/plugin install openai-to-nova-migration@aws-samples-amazon-nova-samples
```

After install, invoke the skill on your OpenAI code with `/openai-to-nova`.

## Prerequisites

- An AWS account with Amazon Bedrock access
- `us.amazon.nova-2-lite-v1:0` enabled in your region
- Python 3.8+ with `boto3` (only needed to run the migrated code)
- `bedrock:InvokeTool` IAM permission if migrating to Nova's built-in web grounding or code interpreter

AWS credentials and Bedrock access are only required when you actually run the migrated code — the migration itself runs inside the host tool.

## Example prompts

```
Migrate this OpenAI code to Amazon Nova 2 Lite:
<paste your openai SDK code>
```

```
I have a GPT-5.2 function-calling app with reasoning_effort="high".
Convert it to Nova 2 Lite.
```

```
Rewrite this GPT-4o multimodal prompt (image input) for Nova 2 Lite.
```

```
Migrate this OpenAI Assistants API app (code interpreter) to Nova 2 Lite.
```

```
We're running a bake-off on Bedrock. Migrate our GPT-5.5 (Responses API) app to Nova 2 Lite.
```

```
Switch this Bedrock gpt-oss-120b Converse call over to Nova 2 Lite.
```

## When NOT to use this skill

- **Anthropic / Claude → Nova migrations** — this skill is OpenAI-specific. Use a Claude-to-Nova migration skill if one exists.
- **Greenfield Nova prompt authoring** (no source model to convert) — use a Nova prompt-optimization skill instead.
- **Accuracy or latency benchmarking** of Nova vs another model — this skill produces migrated code, not evaluation harnesses; use a Nova evaluation skill.
- **Non-Python OpenAI code** — the examples and mappings target the Python `openai` SDK and `boto3`.
- **Titan → Nova embedding migrations** — use the `titan-nova-mme-migration` skill.

## Related resources

- [Amazon Nova 2 User Guide](https://docs.aws.amazon.com/nova/latest/nova2-userguide/getting-started-nova-2.html)
- [Amazon Nova 2 Prompt Engineering Guide](https://docs.aws.amazon.com/nova/latest/nova2-userguide/prompt-engineering-guide.html)
- [Migrate from Amazon Nova 1 to Amazon Nova 2 on Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/migrate-from-amazon-nova-1-to-amazon-nova-2-on-amazon-bedrock/)
- [Amazon Bedrock `converse` API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)
- [Agent Skills open standard — Anthropic](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Amazon Nova Samples](https://github.com/aws-samples/amazon-nova-samples)
