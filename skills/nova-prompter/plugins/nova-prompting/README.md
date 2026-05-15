# Nova Prompting

A Claude Code plugin from the **Amazon Nova** team that adds two slash commands for writing and optimizing prompts for Amazon Nova models:

- **`/nova1-prompt`** — Nova 1 (Micro, Lite, Pro, Premier)
- **`/nova2-prompt`** — Nova 2 Lite (reasoning mode, 1M-token context, multimodal: images, video, documents)

The two skills are strictly separated — `/nova1-prompt` never emits Nova 2 guidance and vice versa.

## Install

```
/plugin marketplace add aws-samples/amazon-nova-samples
/plugin install nova-prompting@amazon-nova-samples
```

Once installed, the two slash commands are available in any Claude Code session.

To update later:

```
/plugin marketplace update amazon-nova-samples
```

To uninstall:

```
/plugin uninstall nova-prompting
```

## Usage

```
/nova1-prompt [paste your prompt here]
/nova2-prompt [paste your prompt here]
```

You can also invoke either command with no argument — the skill will ask you for the prompt and use case.

## What the plugin does

Each command walks you through:

1. **Understand the prompt** — accepts an existing prompt to rewrite, or builds one from scratch from a description of the task.
2. **Identify the use case** — classifies the prompt (general, structured output, RAG, few-shot, chain-of-thought, tool calling, multimodal, etc.) and confirms with you.
3. **Apply the right inference config** — recommends temperature, top-p, and reasoning-mode settings tailored to the use case (e.g. `temperature=0` for structured output, reasoning mode disabled for OCR, etc.).
4. **Rewrite the prompt** — applies Nova-specific formatting:
   - `##Section##` delimiters in place of XML tags
   - canonical section names (`## Task Summary:`, `## Model Instructions:`, etc.)
   - system-prompt hierarchy enforcement
   - chain-of-thought, few-shot, and RAG templates as needed
   - for **Nova 2**: reasoning mode, citation markers, long-context structure, web grounding, and the multimodal system-prompt limitation (task instructions must move to the user prompt for image/video/document use cases)
5. **Return the result** — the rewritten system and user prompts, the recommended inference config as runnable code, and a short list of the changes made.

## Prerequisites

None at install time. The skills run entirely inside your Claude Code session — no Python, no API keys, no AWS setup required. AWS credentials are only needed when you actually run the optimized prompts against Amazon Bedrock.

## Differences between `/nova1-prompt` and `/nova2-prompt`

| Capability | Nova 1 | Nova 2 Lite |
|---|---|---|
| Models | Micro, Lite, Pro, Premier | Lite |
| Reasoning mode | — | ✓ (with effort levels) |
| Context window | up to 300K | up to 1M |
| Multimodal | image, video, document (vision) | image, video, document (full multimodal flow with stricter system-prompt rules) |
| Citation markers | — | ✓ (`%[1]%` inline) |
| Web grounding tool | — | ✓ |
| Constrained-decoding tool calling | — | ✓ |

If you're not sure which one you need, pick `/nova2-prompt` — it covers Nova 2 Lite, which is the current generation.

## Source and feedback

The skill content is generated from the public Amazon Nova prompt-engineering documentation. To file issues or suggest improvements, open an issue on this repository.
