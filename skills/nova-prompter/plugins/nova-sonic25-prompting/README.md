# Nova Sonic 2.5 Prompting

A Claude Code plugin from the **Amazon Nova** team that adds a slash command for writing and reviewing system prompts for Amazon Nova Sonic 2.5 voice agents:

- **`/nova-sonic25-prompt`** — write a new Nova Sonic 2.5 system prompt from a description, rewrite an existing one, or run it against a review checklist before shipping.

This is a separate plugin from [`nova-prompting`](../nova-prompting) (Nova 1 / Nova 2 Lite text and multimodal prompting) — Nova Sonic is a different model family (real-time speech-to-speech) with its own set of rules around tool calling, voice-specific formatting, and safety guardrails.

## Install

```
/plugin marketplace add aws-samples/amazon-nova-samples
/plugin install nova-sonic25-prompting@aws-samples-amazon-nova-samples
```

Once installed, `/nova-sonic25-prompt` is available in any Claude Code session.

To update later:

```
/plugin marketplace update aws-samples-amazon-nova-samples
```

To uninstall:

```
/plugin uninstall nova-sonic25-prompting
```

## Usage

```
/nova-sonic25-prompt [paste your Nova Sonic 2.5 system prompt here]
```

You can also invoke it with no argument — the skill will ask whether you're writing a new prompt from scratch or reviewing/rewriting an existing one.

## What the plugin does

1. **Understand the request** — takes an existing Nova Sonic 2.5 system prompt to review or rewrite, or a description of the voice agent to build from scratch (domain, tools, tone).
2. **Apply the right mode** — generation rules while drafting, or a review checklist against an existing prompt, citing specific rule numbers for any violation found.
3. **Cover the full surface** — system prompt structure, positive framing, tool-calling and tool-description patterns, voice-specific formatting, personalization, date/temporal reliability, and safety guardrails, plus a platform-behavior note for debugging safety-adjacent issues that aren't a plain prompt bug.
4. **Return the result** — the rewritten system prompt and tool descriptions (or the completed checklist for a review), plus a short list of the changes made and why.

## Prerequisites

None at install time. The skill runs entirely inside your Claude Code session — no Python, no API keys, no AWS setup required. AWS credentials are only needed when you actually run the resulting prompt against Amazon Bedrock.

## Source and feedback

The skill content is generalized from field prompt-engineering work on Nova Sonic 2.5 voice agents; it contains no internal filter logic or implementation details of the platform's built-in safety behavior. To file issues or suggest improvements, open an issue on this repository.
