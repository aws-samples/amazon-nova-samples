# Nova Prompter

Prompt-engineering assistants for Amazon Nova, packaged for both **Claude Code** and **Kiro**.

This project ships:

- **Claude Code plugins** that add slash commands for writing and optimizing prompts for Nova 1, Nova 2 Lite, and Nova Sonic 2.5.
- Matching **Kiro powers** that surface the same guidance inside Kiro — one per model family, including a steering file with the full multimodal template catalogue for Nova 2.

The plugins and powers share their underlying guidance: instructions, inference-config tables, multimodal caveats, and section-naming conventions are derived from the public Amazon Nova prompt-engineering documentation. Nova Sonic 2.5's guidance is a separate track — a real-time speech-to-speech model has different rules (voice-specific formatting, tool-calling patterns, safety guardrails) than Nova 1/2 Lite's text and multimodal prompting, so it ships as its own plugin/power rather than reusing the Nova 1/2 flow.

## What's inside

| Slash command (Claude Code) | Power (Kiro) | Purpose |
|---|---|---|
| `/nova1-prompt` | `nova1-prompt` | Rewrite or build prompts for Nova 1 (Micro, Lite, Pro, Premier). |
| `/nova2-prompt` | `nova2-prompt` | Rewrite or build prompts for Nova 2 Lite. Handles text, agentic, and multimodal use cases (image / video / document) and applies the right reasoning-mode and inference config per use case. |
| `/nova-sonic25-prompt` | `nova-sonic25-prompt` | Write or review a system prompt (and tool descriptions) for a Nova Sonic 2.5 voice agent — positive framing, tool-calling patterns, voice formatting, personalization, and safety guardrails. |
| `/nova-migrate` | — | End-to-end migration assistant for porting an application from another LLM to Nova: prompt optimization, baseline capture, rubric-based eval, and a refine loop. *Claude Code only for now.* |

## Install — Claude Code

```
/plugin marketplace add aws-samples/amazon-nova-samples
/plugin install nova-prompting@aws-samples-amazon-nova-samples
```

For Nova Sonic 2.5 specifically:

```
/plugin install nova-sonic25-prompting@aws-samples-amazon-nova-samples
```

To also install the migration assistant:

```
/plugin install nova-migration@aws-samples-amazon-nova-samples
```

After install, run `/reload-plugins` and the slash commands appear automatically.

## Install — Kiro

For Kiro, use the bundled installer:

```bash
git clone <this-repo>
cd <repo>
./install-skills.sh -t kiro -g    # global, all bundles
```

Run with no flags for an interactive prompt that lets you pick the bundle, target tool, and scope. Use `./install-skills.sh -h` for the full flag reference.

## What the plugins / powers actually do

**`/nova1-prompt` and `/nova2-prompt`** walk you through the same flow:

1. Take an existing prompt to optimize, or a description of the task to build one from scratch.
2. Identify the use case — general, structured output, RAG, few-shot, chain-of-thought, tool calling, or one of the multimodal sub-types.
3. Apply the right inference config — temperature, top-p, reasoning mode, etc., per the official Nova guidance for that use case.
4. Rewrite the prompt with Nova-specific formatting: `##Section##` headers in place of XML tags, canonical section names (`## Task Summary:`, `## Model Instructions:` etc.), system-prompt hierarchy enforcement, and chain-of-thought / few-shot / RAG templates as needed.
5. Return the rewritten system and user prompts, the recommended inference config as runnable code, and a short list of the changes made.

For Nova 2 multimodal use cases, the plugins explicitly enforce the system-prompt limitation (task instructions must live in the user prompt, not the system prompt), and the Kiro power loads a separate steering file with the full template catalogue.

**`/nova-sonic25-prompt`** follows a different flow, since Nova Sonic 2.5 is a voice model with different failure modes than text prompting:

1. Take an existing Nova Sonic 2.5 system prompt to review/rewrite, or a description of the voice agent to build.
2. Either apply the generation rules while drafting, or run a review checklist against an existing prompt — citing specific rule numbers for any violation.
3. Cover system-prompt structure, positive framing, tool-calling/tool-description patterns, voice-specific formatting, personalization, date/temporal reliability, and safety guardrails.
4. Return the system prompt and tool descriptions (or the completed checklist), plus the reasoning behind each change.

## Prerequisites

None at install time. The plugins / powers run inside the host tool (Claude Code or Kiro) — no Python, no API keys, no AWS setup. AWS credentials are only needed when you actually run the optimized prompts against Amazon Bedrock.

## Privacy and telemetry

These plugins and powers do not collect telemetry. All prompt processing happens inside the host tool — no data is sent to AWS, Amazon, or any third party by this project. Your Claude Code or Kiro session may, separately, send the prompt content to whichever model your session is configured to use.

## License

MIT-0 (MIT No Attribution) — distributed as part of [aws-samples/amazon-nova-samples](https://github.com/aws-samples/amazon-nova-samples). The repository's root [LICENSE](../../LICENSE) applies.

## Author

Maintained by the Amazon Nova team.
