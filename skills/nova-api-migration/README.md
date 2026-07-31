# Nova API Migration

Migrate Python LLM application **API code** from Google Gemini, OpenAI, or Anthropic Claude to Amazon Nova 2 Lite on Amazon Bedrock.

Ships in two forms from the same guidance: a **skill** for Claude Code and Codex, and a **Kiro power**. See [Installation](#installation) for each. ("Skill" is used below as the generic term for the capability.)

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

Codex discovers skills from `.agents/skills/` directories and can also install plugins from a marketplace.

**Option A — local skill (simplest for Codex CLI).** Copy (or symlink) the skill into a skills directory Codex scans — repo-level `.agents/skills/` or user-level `~/.agents/skills/`:

```bash
mkdir -p .agents/skills
cp -r skills/nova-api-migration/plugins/nova-api-migration/skills/nova-api-migration \
      .agents/skills/nova-api-migration
```

Codex picks it up automatically; restart Codex if it doesn't appear.

**Option B — plugin marketplace.** Add this repo as a marketplace source (Codex reads the repo-root `.claude-plugin/marketplace.json` as a legacy-compatible catalog), then install the `nova-api-migration` plugin from the Plugins directory:

```bash
codex plugin marketplace add aws-samples/amazon-nova-samples
```

Publishing to the public OpenAI plugin directory is a separate step — submit through the OpenAI plugin submission portal.

### Kiro

This skill is also packaged as a Kiro **power** at [`powers/nova-api-migration/`](./powers/nova-api-migration/). It's a Knowledge Base power (pure documentation, no MCP server): a router `POWER.md` plus on-demand steering files.

**Install via the Powers panel.** Open the command palette and search "Powers" (or ask Kiro to open the powers configuration), then install the `nova-api-migration` power. Registering through the panel is what makes Kiro pick it up — simply copying the folder into `.kiro/powers/` is not detected by a running session (reload Kiro if you install by hand).

Once installed, Kiro activates the power automatically based on its keywords (e.g. "migrate to nova", "gemini to nova") — no slash command needed.


### Manual (any agent)

Clone the repo and point your agent at the skill entry point:

```bash
git clone https://github.com/aws-samples/amazon-nova-samples.git
# Claude Code / Codex plugin: amazon-nova-samples/skills/nova-api-migration/plugins/nova-api-migration/
# Kiro power:                 amazon-nova-samples/skills/nova-api-migration/powers/nova-api-migration/POWER.md
```

## Verify it works

After installing, run this quick smoke test. Paste this prompt into the assistant:

```
Migrate this to Nova 2 Lite:

from openai import OpenAI
client = OpenAI()
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Say hi."},
    ],
    max_tokens=50,
)
print(resp.choices[0].message.content)
```

**A correct result shows the migration guidance is loaded** — the output should:
- Use `boto3` `bedrock-runtime` `converse` with `modelId="us.amazon.nova-2-lite-v1:0"`
- Move the system message into a top-level `system=[{"text": "..."}]`
- Wrap message content in typed blocks (`"content": [{"text": "..."}]`)
- Nest `max_tokens` as `inferenceConfig={"maxTokens": 50}`
- Parse the response as `response["output"]["message"]["content"][0]["text"]`

If it produces generic boto3 code without these specifics (especially the system extraction and typed content blocks), the skill/power isn't being picked up — recheck the install.

Per-tool confirmation that it's installed:

- **Claude Code** — after `/plugin install`, the plugin appears in `/plugin` (Installed). Then run the smoke test.
- **Codex** — run `/skills` (or type `$` ) to confirm `nova-api-migration` is listed; then run the smoke test.
- **Kiro** — after installing in the Powers panel, just run the smoke test; the power activates on the migration keywords. (You'll see it load `nova-target.md` and the OpenAI guide.)

## Prerequisites

**To install and use this skill/power: none.** It runs inside your coding assistant and only reads and rewrites code — no Python, no API keys, no AWS setup required.

**To actually run the migrated code it produces**, you'll need:

- An AWS account with Amazon Bedrock model access enabled for Nova 2 Lite
- AWS credentials configured (IAM role, profile, or environment variables)
- Python with `boto3` installed

## Usage

Install this skill (or power) in your coding assistant, then ask it to migrate your code.

### You don't need to name the source provider

The skill **auto-detects** the source provider from the code you paste — from imports and client calls such as `from google import genai` / `client.models.generate_content` (Gemini), `from openai import OpenAI` / `client.chat.completions.create` (OpenAI), or `from anthropic import Anthropic` / `client.messages.create` (Claude, including `boto3` `converse` with an `anthropic.claude-*` modelId). So the simplest effective prompt is just paste the code and state the intent:

```
Migrate this to Nova 2 Lite:

<paste your Python code>
```

### When to add detail

Naming the source never hurts, and a few cases benefit from extra context:

- **Ambiguous or partial snippets** — if there's no import or client call to detect, the skill will ask you which provider it is. Naming it upfront skips that round-trip.
- **OpenAI on Bedrock vs. the OpenAI API** — these migrate differently (gpt-oss on Converse is nearly a one-line `modelId` swap). Mention "this already runs on Bedrock" to get the lighter path immediately.
- **Region and reasoning** — it defaults to `us.amazon.nova-2-lite-v1:0` and will ask about region and reasoning effort when relevant. Pre-empt with, e.g., "target eu-west-1, keep reasoning off".

A fully specified prompt looks like:

```
Migrate this Gemini (google-genai) code to Nova 2 Lite, us-east-1, no reasoning:

<paste your code>
```

More example prompts:

```
Convert my Gemini application to use Amazon Bedrock Nova
```

```
I have a Claude-on-Bedrock app using claude-3-5-haiku, switch it to Nova 2 Lite
```

> **Note:** Auto-detection only works when the assistant can see the code. A bare "migrate my app to Nova" with nothing attached will prompt you for the code or provider first.

The skill will:
1. Detect the source provider and SDK pattern (or ask, if it can't)
2. Identify features used (tools, structured output, multimodal, reasoning, etc.)
3. Flag any features that cannot migrate 1:1 and suggest alternatives
4. Produce working migrated code with explanations of every change

## When NOT to Use This Skill

- **Prompt rewriting for Nova best practices** → use `nova-prompter`
- **Non-Python SDKs** (JavaScript, Java, Go) → not yet covered
- **Nova Sonic migrations** → different model family

## Related Skills

- [nova-prompter](../nova-prompter/) — optimize prompts for Nova formatting conventions
- [titan-nova-mme-migration](../titan-nova-mme-migration/) — migrate from Titan to Nova multimodal

## Folder Structure

The skill ships for two host tools, each under its own top-level folder:

- **`plugins/`** — the Claude Code + Codex skill (entry point `SKILL.md`).
- **`powers/`** — the Kiro power (entry point `POWER.md`).

```
nova-api-migration/
├── README.md                         # This file
│
├── plugins/                          # ── Claude Code + Codex ──
│   └── nova-api-migration/           # Plugin root (manifests + bundled skills)
│       ├── .claude-plugin/
│       │   └── plugin.json           # Claude Code plugin manifest
│       ├── .codex-plugin/
│       │   └── plugin.json           # Codex plugin manifest ("skills": "./skills/")
│       └── skills/
│           └── nova-api-migration/   # The skill
│               ├── SKILL.md          # Entry point — detects provider, routes to source guide
│               ├── references/
│               │   └── nova-target.md    # Shared Nova API contract (model IDs, inference, tools, validation)
│               ├── gemini/
│               │   ├── SKILL.md      # Gemini source guide
│               │   └── references/
│               │       ├── feature-mapping.md
│               │       ├── code-examples.md
│               │       └── generate-content-patterns.md  # Deprecated SDK & Interactions API patterns
│               ├── openai/
│               │   ├── SKILL.md      # OpenAI source guide
│               │   └── references/
│               │       ├── feature-mapping.md
│               │       ├── code-examples.md
│               │       └── openai-on-bedrock-patterns.md  # GPT-5.x and gpt-oss on Bedrock
│               └── claude/
│                   ├── SKILL.md      # Claude source guide
│                   └── references/
│                       ├── feature-mapping.md
│                       └── code-examples.md
│
└── powers/                           # ── Kiro ──
    └── nova-api-migration/           # Knowledge Base power
        ├── POWER.md                  # Router: provider detection + steering-file index
        └── steering/                 # On-demand guides, loaded per detected provider
            ├── nova-target.md        # Shared Nova API contract (always loaded)
            ├── gemini.md             # Gemini source guide
            ├── gemini-feature-mapping.md
            ├── gemini-code-examples.md
            ├── gemini-generate-content-patterns.md
            ├── openai.md             # OpenAI source guide
            ├── openai-feature-mapping.md
            ├── openai-code-examples.md
            ├── openai-on-bedrock-patterns.md
            ├── claude.md             # Claude source guide
            ├── claude-feature-mapping.md
            └── claude-code-examples.md
```
