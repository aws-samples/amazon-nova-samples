---
name: nova-migration
description: Migrate LLM application code and prompts to Amazon Nova 2 Lite on Amazon Bedrock. Use when converting code from Google Gemini (google-genai / google-generativeai) or Anthropic Claude (anthropic Messages API or Claude-on-Bedrock) to Nova 2 Lite (boto3 Bedrock Runtime converse), rewriting prompts for Nova format, or migrating function calling, structured output, multimodal, or reasoning features to Nova.
tags: [skill, migration, nova, bedrock, gemini, claude, anthropic]
---

# Migrate to Amazon Nova 2 Lite

Migrate Python application code and prompts from another LLM provider to Amazon Nova 2 Lite on
Amazon Bedrock. This skill has two halves:

- A **shared Nova target** (`references/nova-target.md`) — the rules for what to produce on the
  Nova side. Identical for every source provider, written once.
- A **per-source guide** (`gemini/`, `claude/`, …) — how to read and detect the source code, the
  full source→Nova mapping tables, before/after examples, and what can't migrate 1:1.

## Step 1: Identify the source provider

Determine which provider the code is migrating FROM, then read that source skill and follow it:

| Source | Detected from | Read |
|--------|---------------|------|
| **Google Gemini** | `from google import genai`, `import google.generativeai`, `client.models.generate_content`, `client.interactions.create` | `gemini/SKILL.md` |
| **Anthropic Claude** | `from anthropic import Anthropic`, `client.messages.create`, `AnthropicBedrock`; or `boto3` `converse` with an `anthropic.claude-*` `modelId` | `claude/SKILL.md` |

If the source provider is unclear, ask the user before proceeding. If it's a provider not yet
covered here (e.g., OpenAI), tell the user it's not yet supported rather than guessing a mapping.

## Step 2: Follow the source skill

Each source `SKILL.md` is self-contained: it walks the analyze → classify → migrate code →
migrate prompt → structured output → tools → present → validate workflow for that provider, and
points to `references/nova-target.md` for every Nova-side decision (model IDs, inference config,
reasoning effort, `##Section##` prompt format, tool shape, validation checklist).

You **MUST** read both the source `SKILL.md` and `references/nova-target.md` before producing a
migration — the source skill covers the FROM side, the target file covers the TO side.

## What this skill produces

Every migration delivers two things: **working migrated code** (boto3 Bedrock `converse`) and an
**explanation of every change**, including any source features that can't be ported 1:1.

## Adding a new source provider

To extend this skill to another provider, add a sibling directory (e.g. `openai/`) with its own
`SKILL.md` + `references/`, register it in Step 1's table, and reuse `references/nova-target.md`
unchanged for the Nova side.
