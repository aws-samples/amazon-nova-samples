# Nova Prompter

Prompt-engineering assistants for Amazon Nova, packaged for both **Claude Code** and **Kiro**.

This project ships:

- Two **Claude Code plugins** that add slash commands for writing and optimizing prompts for Nova 1 and Nova 2 Lite.
- Two **Kiro powers** that surface the same guidance inside Kiro — one for Nova 1, one for Nova 2 Lite — including a steering file with the full multimodal template catalogue for Nova 2.

The plugins and powers share their underlying guidance: instructions, inference-config tables, multimodal caveats, and section-naming conventions are derived from the public Amazon Nova prompt-engineering documentation.

## What's inside

| Slash command (Claude Code) | Power (Kiro) | Purpose |
|---|---|---|
| `/nova1-prompt` | `nova1-prompt` | Rewrite or build prompts for Nova 1 (Micro, Lite, Pro, Premier). |
| `/nova2-prompt` | `nova2-prompt` | Rewrite or build prompts for Nova 2 Lite. Handles text, agentic, and multimodal use cases (image / video / document) and applies the right reasoning-mode and inference config per use case. |
| `/nova-migrate` | — | End-to-end migration assistant for porting an application from another LLM to Nova: prompt optimization, baseline capture, rubric-based eval, and a refine loop. *Claude Code only for now.* |

## Install — Claude Code

```
/plugin marketplace add aws-samples/amazon-nova-samples
/plugin install nova-prompting@amazon-nova-samples
```

To also install the migration assistant:

```
/plugin install nova-migration@amazon-nova-samples
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

Each one walks you through the same flow:

1. Take an existing prompt to optimize, or a description of the task to build one from scratch.
2. Identify the use case — general, structured output, RAG, few-shot, chain-of-thought, tool calling, or one of the multimodal sub-types.
3. Apply the right inference config — temperature, top-p, reasoning mode, etc., per the official Nova guidance for that use case.
4. Rewrite the prompt with Nova-specific formatting: `##Section##` headers in place of XML tags, canonical section names (`## Task Summary:`, `## Model Instructions:` etc.), system-prompt hierarchy enforcement, and chain-of-thought / few-shot / RAG templates as needed.
5. Return the rewritten system and user prompts, the recommended inference config as runnable code, and a short list of the changes made.

For Nova 2 multimodal use cases, the plugins explicitly enforce the system-prompt limitation (task instructions must live in the user prompt, not the system prompt), and the Kiro power loads a separate steering file with the full template catalogue.

## Prerequisites

None at install time. The plugins / powers run inside the host tool (Claude Code or Kiro) — no Python, no API keys, no AWS setup. AWS credentials are only needed when you actually run the optimized prompts against Amazon Bedrock.

## Privacy and telemetry

These plugins and powers do not collect telemetry. All prompt processing happens inside the host tool — no data is sent to AWS, Amazon, or any third party by this project. Your Claude Code or Kiro session may, separately, send the prompt content to whichever model your session is configured to use.

## License

MIT-0 (MIT No Attribution) — distributed as part of [aws-samples/amazon-nova-samples](https://github.com/aws-samples/amazon-nova-samples). The repository's root [LICENSE](../../LICENSE) applies.

## Author

Maintained by the Amazon Nova team.
