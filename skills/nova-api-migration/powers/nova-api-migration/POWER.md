---
name: "nova-api-migration"
displayName: "Nova API Migration"
description: "Migrate Python LLM application API code from Google Gemini, OpenAI, or Anthropic Claude to Amazon Nova 2 Lite on Amazon Bedrock (boto3 Converse API). Handles SDK swap, authentication, request/response reshaping, tool calling, structured output, multimodal content, streaming, and reasoning configuration. Does not cover prompt optimization — use the nova-prompter power for that."
keywords: ["nova api migration", "bedrock converse", "migrate to nova", "gemini to nova", "openai to nova", "claude to nova", "boto3"]
author: "Amazon Nova"
---

# Nova API Migration

## Overview

Migrate Python application **API code** from another LLM provider to Amazon Nova 2 Lite on Amazon Bedrock. This power handles the SDK, authentication, request structure, response parsing, tool calling, structured output, multimodal content, streaming, and reasoning configuration.

It does **not** rewrite prompts for Nova's formatting conventions. If the user also needs prompt optimization after the API migration, point them to the **nova-prompter** power.

**Supported source providers:**

| Provider | SDK patterns covered |
|----------|----------------------|
| Google Gemini | `google-genai` (generateContent, Interactions API), deprecated `google-generativeai` |
| OpenAI | Chat Completions, Responses, Assistants API, and OpenAI-on-Bedrock (GPT-5.x, gpt-oss) |
| Anthropic Claude | Anthropic Messages API, Claude-on-Bedrock (model swap) |

## Architecture

- A **shared Nova target** (`nova-target.md`) — the API contract for what to produce on the Nova side. Identical for every source provider, so it is written once and always loaded.
- A **per-source guide** (`gemini.md`, `openai.md`, `claude.md`) — how to detect the source SDK, the full source→Nova mapping, before/after examples, and features that cannot migrate 1:1.

## Available Steering Files

Load only what the migration needs — do not load every file upfront.

**Always load:**
- **nova-target.md** — the shared Nova 2 Lite API contract: model IDs, inference-config tables, reasoning-effort rules, tool shape, structured output, streaming, and the validation checklist.

**Load the one matching the detected source provider:**
- **gemini.md** — Google Gemini source guide (detection, workflow, quick reference, common mistakes).
- **openai.md** — OpenAI source guide (Chat Completions / Responses / Assistants / OpenAI-on-Bedrock).
- **claude.md** — Anthropic Claude source guide (Messages API and Claude-on-Bedrock).

**Load deeper references on demand, per the source guide's instructions:**
- **gemini-feature-mapping.md**, **gemini-code-examples.md**, **gemini-generate-content-patterns.md** (deprecated SDK / Interactions API)
- **openai-feature-mapping.md**, **openai-code-examples.md**, **openai-on-bedrock-patterns.md**
- **claude-feature-mapping.md**, **claude-code-examples.md**

## Workflow

### Step 1: Identify the source provider

Determine which provider the code is migrating **FROM**, then load that provider's steering file and `nova-target.md`.

| Source | Detected from | Load |
|--------|---------------|------|
| Google Gemini | `from google import genai`, `import google.generativeai`, `client.models.generate_content`, `client.interactions.create` | `gemini.md` |
| OpenAI | `from openai import OpenAI`, `client.chat.completions.create`, `client.responses.create`, `client.beta.assistants`, or the OpenAI SDK pointed at a Bedrock base URL | `openai.md` |
| Anthropic Claude | `from anthropic import Anthropic`, `client.messages.create`, `AnthropicBedrock`; or `boto3` `converse` with an `anthropic.claude-*` `modelId` | `claude.md` |

If the source provider is unclear, ask the user before proceeding.

### Step 2: Follow the source guide

Each source guide is self-contained: it walks the analyze → classify → migrate → structured output → tools → present → validate workflow for that provider, and points to `nova-target.md` for every Nova-side API decision (model IDs, inference config, reasoning config, tool shape, validation checklist).

Load **both** the matching source guide **and** `nova-target.md` (via `readSteering`) before producing a migration.

## What this power produces

1. **Working migrated code** — boto3 Bedrock Runtime `converse` API calls that compile and run.
2. **Explanation of every API change** — including any source features that cannot be ported 1:1.

## What this power does NOT produce

- **Prompt optimization** — this power preserves prompt content as-is (only restructuring what the API change requires, like extracting a system prompt out of the messages array). For Nova-optimized prompt formatting (`##Section##` delimiters, long-context templates, suppression guardrails), use the **nova-prompter** power.
- **Infrastructure provisioning** — IAM roles, Bedrock model access, VPC config.
- **Accuracy benchmarking** — use evaluation tooling to compare output quality.

## Best Practices

- Always load `nova-target.md` — the Nova-side rules (reasoning-effort handling, inference-config-by-use-case, validation checklist) are identical across providers and defined only there.
- Confirm findings with the user after each workflow step, especially any features flagged as "cannot migrate 1:1."
- Do not copy the source model's reasoning-token budget directly to Nova; present the Nova effort levels and let the user choose.
- Run the validation checklist in `nova-target.md` before presenting any migration.

## Adding a new source provider

The Nova side never changes — reuse `nova-target.md` unchanged. Only the source-specific material is new. To add a provider (e.g. Cohere):

1. **Add the guide** — create `<provider>.md` (e.g. `cohere.md`): detection signals, the source→Nova mapping, features that cannot migrate 1:1, and at least one before/after example.
2. **Add any deeper references only if needed** — most providers need just the guide. Add a separate steering file *only* for genuinely conditional/niche material (e.g. a deprecated SDK, or a Bedrock-hosted variant), never as a default.
3. **Register it** — add a row to the Step 1 detection table and an entry under "Available Steering Files".
4. **Do not touch `nova-target.md`** — the Nova contract is shared across all providers.

### Naming convention

The `steering/` folder is flat (Kiro loads steering files by filename, with no subdirectories), so naming is how files stay organized:

- `nova-target.md` — the shared Nova contract (always loaded).
- `<provider>.md` — the required per-provider guide (e.g. `gemini.md`).
- `<provider>-<topic>.md` — optional, conditional references only (e.g. `gemini-generate-content-patterns.md`, `openai-on-bedrock-patterns.md`).

Keep the per-provider footprint small — prefer a single `<provider>.md` plus only the conditional extras that a subset of migrations actually need. This keeps the folder and this router readable as more providers are added.

## Privacy and telemetry

This power does not collect telemetry. All processing happens inside your local Kiro session — no code, prompt content, or usage data is sent to AWS, Amazon, or any third party by this power. Your Kiro session may, separately, send content to whichever model your session is configured to use.

## License

MIT-0 (MIT No Attribution). Distributed as part of [aws-samples/amazon-nova-samples](https://github.com/aws-samples/amazon-nova-samples); the repository's root `LICENSE` file applies. This power is pure documentation — it bundles no MCP servers, so no third-party MCP licenses apply.
