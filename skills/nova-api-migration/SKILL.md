---
name: nova-api-migration
description: Migrate LLM application API code to Amazon Nova 2 Lite on Amazon Bedrock. Use when converting Python API code from Google Gemini (google-genai / google-generativeai), OpenAI (openai SDK — Chat Completions, Responses, or Assistants API), or Anthropic Claude (anthropic Messages API or Claude-on-Bedrock) to Nova 2 Lite (boto3 Bedrock Runtime converse API). Covers SDK swap, authentication, request/response reshaping, tool calling, structured output, multimodal, streaming, and reasoning config. Does NOT cover prompt optimization — use the nova-prompter skill for that.
tags: [skill, migration, api, nova, bedrock, gemini, openai, claude, anthropic]
---

# Migrate API Code to Amazon Nova 2 Lite

Migrate Python application **API code** from another LLM provider to Amazon Nova 2 Lite on Amazon Bedrock. This skill handles the SDK, authentication, request structure, response parsing, tool calling, structured output, multimodal content, streaming, and reasoning configuration.

**This skill does NOT cover prompt optimization.** If the customer also needs to rewrite their prompts for Nova's formatting conventions, instruct them to install and use the **nova-prompter** skill after the API migration is complete.

## Architecture

- A **shared Nova target** (`references/nova-target.md`) — the API contract for what to produce on the Nova side. Identical for every source provider, written once.
- A **per-source guide** (`gemini/`, `openai/`, `claude/`) — how to detect the source SDK, the full source→Nova API mapping tables, before/after code examples, and features that cannot migrate 1:1.

## Step 1: Identify the source provider

Determine which provider the code is migrating FROM, then read that source guide and follow it:

| Source | Detected from | Read |
|--------|---------------|------|
| **Google Gemini** | `from google import genai`, `import google.generativeai`, `client.models.generate_content`, `client.interactions.create` | `gemini/SKILL.md` |
| **OpenAI** | `from openai import OpenAI`, `client.chat.completions.create`, `client.responses.create`, `client.beta.assistants`, or OpenAI SDK pointed at a Bedrock base URL | `openai/SKILL.md` |
| **Anthropic Claude** | `from anthropic import Anthropic`, `client.messages.create`, `AnthropicBedrock`; or `boto3` `converse` with an `anthropic.claude-*` `modelId` | `claude/SKILL.md` |

If the source provider is unclear, ask the user before proceeding.

## Step 2: Follow the source guide

Each source `SKILL.md` is self-contained: it walks the analyze → classify → migrate code → structured output → tools → present → validate workflow for that provider, and points to `references/nova-target.md` for every Nova-side API decision (model IDs, inference config, reasoning config, tool shape, validation checklist).

You **MUST** read both the source `SKILL.md` and `references/nova-target.md` before producing a migration.

## What this skill produces

Every migration delivers two things:
1. **Working migrated code** — boto3 Bedrock Runtime `converse` API calls that compile and run
2. **Explanation of every API change** — including any source features that cannot be ported 1:1

## What this skill does NOT produce

- **Prompt optimization** — this skill preserves prompt content as-is (only restructuring what's necessary for the API change, like extracting system prompts from the messages array). For Nova-optimized prompt formatting (`##Section##` delimiters, long-context templates, suppression guardrails), use the **nova-prompter** skill.
- **Infrastructure provisioning** — IAM roles, Bedrock model access, VPC config
- **Accuracy benchmarking** — use evaluation skills to compare output quality

## Adding a new source provider

To extend this skill to another provider, add a sibling directory (e.g. `cohere/`) with its own `SKILL.md` + `references/`, register it in Step 1's table, and reuse `references/nova-target.md` unchanged for the Nova side.
