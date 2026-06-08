# Migrate to Amazon Nova 2 Lite

An [Agent Skill](https://agentskills.io/specification) that migrates LLM application code and prompts to [Amazon Nova 2 Lite](https://docs.aws.amazon.com/nova/latest/userguide/) (`us.amazon.nova-2-lite-v1:0`) on Amazon Bedrock.

One plugin covers multiple source providers. It is split into a **shared Nova target** (written once) and a **per-source guide** (one per provider), so the Nova-side rules never duplicate across sources.

## Supported sources

| Source | Detected from |
|---|---|
| **Google Gemini** 2.0 / 2.5 / 3.x | `from google import genai`, `import google.generativeai`, `client.models.generate_content`, `client.interactions.create` |
| **Anthropic Claude** 3 / 3.5 / Haiku 4.5 | `from anthropic import Anthropic`, `client.messages.create`, `AnthropicBedrock`; or `boto3` `converse` with an `anthropic.claude-*` `modelId` |

**Target:** `us.amazon.nova-2-lite-v1:0`

## Skill structure

```
nova-migration/
├── SKILL.md                              # Router — detects the source provider, dispatches
├── README.md                             # This file
├── references/
│   └── nova-target.md                    # SHARED Nova side: model IDs, inference config,
│                                         #   reasoning, ##Section## format, tools, validation
├── gemini/
│   ├── SKILL.md                          # Gemini source guide (FROM side)
│   └── references/
│       ├── feature-mapping.md            # Gemini → Nova mapping tables
│       ├── code-examples.md              # before/after patterns
│       └── generate-content-patterns.md  # generateContent / Interactions API / deprecated SDK
└── claude/
    ├── SKILL.md                          # Claude source guide (FROM side)
    └── references/
        ├── feature-mapping.md            # Claude → Nova mapping tables
        ├── code-examples.md              # before/after patterns (both surfaces)
        └── messages-api-patterns.md      # Anthropic Messages API / AnthropicBedrock / async / streaming
```

## How it works

1. The top-level `SKILL.md` detects which provider the code is migrating **from** and routes to that
   source guide (`gemini/SKILL.md` or `claude/SKILL.md`).
2. The source guide walks the analyze → migrate code → migrate prompt → tools → validate workflow
   for that provider's **FROM** side.
3. For every Nova-side decision (model IDs, inference config, reasoning effort, `##Section##` prompt
   format, tool shape, validation checklist), the source guide points to the shared
   `references/nova-target.md` — so the Nova target is defined exactly once.

This is why it's one plugin rather than several: the **source side** diverges per provider (SDK,
auth, tool-schema format, prompt idioms), but the **target side** is identical. Keeping the target
shared means a Nova API change is fixed in one file, not once per source.

## Adding a new source provider

Add a sibling directory (e.g. `openai/`) with its own `SKILL.md` + `references/`, register it in the
router table in the top-level `SKILL.md`, and reuse `references/nova-target.md` unchanged.

## Installation

### Claude Code

This skill ships as the `nova-migration` plugin via the `aws-samples-amazon-nova-samples` marketplace.

```
/plugin marketplace add https://github.com/aws-samples/amazon-nova-samples
/plugin install nova-migration@aws-samples-amazon-nova-samples
```

After install, invoke it on your code with `/nova-migration`.

## Prerequisites

- An AWS account with Amazon Bedrock access
- `us.amazon.nova-2-lite-v1:0` enabled in your region
- Python 3.8+ with `boto3` (only needed to run the migrated code)

AWS credentials and Bedrock access are only required when you run the migrated code — the migration
itself runs inside the host tool.

## Example prompts

```
Migrate this Gemini code to Amazon Nova 2 Lite:
<paste your google-genai code>
```

```
I have a Claude 3.5 Haiku tool-use app on the Anthropic Messages API. Convert it to Nova 2 Lite.
```

```
We already run Claude 3 Haiku through Bedrock converse. Re-point it to Nova 2 Lite and rewrite the prompt.
```

## Related resources

- [Amazon Nova User Guide](https://docs.aws.amazon.com/nova/latest/userguide/)
- [Amazon Bedrock `converse` API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)
- [Agent Skills open standard — Anthropic](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Amazon Nova Samples](https://github.com/aws-samples/amazon-nova-samples)
