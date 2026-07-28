# Nova API Migration Skill

Migrate Python LLM application **API code** from Google Gemini, OpenAI, or Anthropic Claude to Amazon Nova 2 Lite on Amazon Bedrock.

## What This Skill Does

Transforms SDK calls, authentication, request/response structure, tool calling, structured output, multimodal content, streaming, and reasoning configuration from a source provider to the Bedrock Converse API.

## What This Skill Does NOT Do

- **Prompt optimization** — use the [nova-prompter](../nova-prompter/) skill for Nova-optimized prompt formatting
- **Infrastructure setup** — IAM roles, Bedrock model access, VPC configuration
- **Accuracy benchmarking** — use evaluation tools to compare output quality

## Supported Source Providers

| Provider | SDK Patterns Covered |
|----------|---------------------|
| **Google Gemini** | `google-genai` (generateContent, Interactions API), deprecated `google-generativeai` |
| **OpenAI** | Chat Completions, Responses API, Assistants API, OpenAI-on-Bedrock (GPT-5.x, gpt-oss) |
| **Anthropic Claude** | Anthropic Messages API, Claude-on-Bedrock (model swap) |

## Installation

### Claude Code

Add the `aws-samples/amazon-nova-samples` marketplace, then install the plugin:

```
/plugin marketplace add aws-samples/amazon-nova-samples
/plugin install nova-api-migration@aws-samples-amazon-nova-samples
```

### Codex

Include the skill from the release tarball or reference it in your `AGENTS.md`:

```
include: aws-samples/amazon-nova-samples/skills/nova-api-migration/SKILL.md
```

### Kiro

Enable the **Nova API Migration** power from the Kiro registry.

### Manual (any agent)

Clone the repo and point your agent at the skill entry point:

```bash
git clone https://github.com/aws-samples/amazon-nova-samples.git
# Reference: amazon-nova-samples/skills/nova-api-migration/SKILL.md
```

## Prerequisites

- AWS account with Bedrock model access enabled for Nova 2 Lite
- AWS credentials configured (IAM role, profile, or environment variables)
- Python with `boto3` installed

## Usage

Install this skill in your coding assistant, then ask it to migrate your code:

```
Migrate this OpenAI code to Nova 2 Lite: [paste code]
```

```
Convert my Gemini application to use Amazon Bedrock Nova
```

```
I have a Claude-on-Bedrock app using claude-3-5-haiku, switch it to Nova 2 Lite
```

The skill will:
1. Detect the source provider and SDK pattern
2. Identify features used (tools, structured output, multimodal, reasoning, etc.)
3. Flag any features that cannot migrate 1:1 and suggest alternatives
4. Produce working migrated code with explanations of every change

## When NOT to Use This Skill

- **Prompt rewriting for Nova best practices** → use `nova-prompter`
- **Greenfield Nova development** (no source code to migrate) → use `nova-prompter`
- **Non-Python SDKs** (JavaScript, Java, Go) → not yet covered
- **Nova Canvas / Nova Sonic migrations** → different model families

## Related Skills

- [nova-prompter](../nova-prompter/) — optimize prompts for Nova formatting conventions
- [titan-nova-mme-migration](../titan-nova-mme-migration/) — migrate from Titan to Nova multimodal

## Skill Structure

```
nova-api-migration/
├── SKILL.md                          # Entry point — detects provider, routes to source guide
├── README.md                         # This file
├── references/
│   └── nova-target.md                # Shared Nova API contract (model IDs, inference, tools, validation)
├── gemini/
│   ├── SKILL.md                      # Gemini source guide
│   └── references/
│       ├── feature-mapping.md        # Complete Gemini → Nova API mapping
│       ├── code-examples.md          # Before/after code examples
│       └── generate-content-patterns.md  # Deprecated SDK & Interactions API patterns
├── openai/
│   ├── SKILL.md                      # OpenAI source guide
│   └── references/
│       ├── feature-mapping.md        # Complete OpenAI → Nova API mapping
│       ├── code-examples.md          # Before/after code examples
│       └── openai-on-bedrock-patterns.md  # GPT-5.x and gpt-oss on Bedrock
├── claude/
│   ├── SKILL.md                      # Claude source guide
│   └── references/
│       ├── feature-mapping.md        # Complete Claude → Nova API mapping
│       └── code-examples.md          # Before/after code examples
├── examples/
│   └── basic-text-generation/        # Worked example: all 3 providers → Nova
├── .claude-plugin/
│   └── plugin.json                   # Claude Code plugin manifest
└── .codex-plugin/
    └── plugin.json                   # Codex plugin manifest
```
