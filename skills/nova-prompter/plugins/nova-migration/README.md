# Nova Migration

Claude Code plugin that adds an end-to-end migration assistant for porting an application from another LLM to Amazon Nova:

- **`/nova-migrate`** — orchestrates prompt optimization, baseline capture from the source model, rubric-based evaluation, and a refine loop that re-optimizes when Nova regresses.

## What it does

Given a source prompt written for another model (Claude, GPT, Llama, etc.), `/nova-migrate` will:

1. **Ingest** the source prompt and your test data (or generate synthetic tests if you don't have any).
2. **Baseline** — run your tests through the source model, capture outputs.
3. **Optimize** — delegate to `/nova1-prompt` or `/nova2-prompt` to produce a Nova version.
4. **Derive a rubric** from your task description (shown to you for edits before scoring).
5. **Evaluate** — run tests through Nova with the new prompt; LLM-as-judge scores each output against the rubric and the baseline.
6. **Refine loop** — if Nova regresses on any test, feed the failures back into the optimizer and try again (up to 3 iterations by default).
7. **Report** — a markdown report with per-test scores, side-by-side diffs, iteration history, and a ship/no-ship verdict.

## Install

### Plugin dependency

`/nova-migrate` calls `/nova1-prompt` and `/nova2-prompt` at runtime, so you need both plugins:

```
/plugin marketplace add <this-repo-url>
/plugin install nova-prompting
/plugin install nova-migration
```

Or via shell script:

```bash
./install-skills.sh -b all -t claude -g
```

### Runtime prerequisites

Unlike the prompting plugin, `/nova-migrate` shells out to a Python helper for actual model calls. You'll need:

- **Python 3.12+**
- **`uv`** (recommended — the skill invokes `uv run ...`). Install: <https://docs.astral.sh/uv/>
- **AWS credentials** for Amazon Bedrock, configured via `aws configure`, `AWS_PROFILE`, or any standard boto3 credential source. The migration target (Nova) always runs on Bedrock, so this is required.
- **Optional** — if you want to baseline against a non-Bedrock source model:
  - `OPENAI_API_KEY` for `openai:<model-id>` source models
  - `ANTHROPIC_API_KEY` for `anthropic:<model-id>` source models

No API keys are needed if you use the `--baseline-from-tests` mode, where you provide `expected_output` in each test instead of calling the source model.

## Usage

In a Claude Code session:

```
/nova-migrate
```

The skill will ask for:

1. **Target Nova generation** — Nova 1 or Nova 2.
2. **Source prompt** — file path, repo dir, or pasted inline.
3. **Task description** — one or two sentences describing what the prompt does. Used for synthetic test generation and rubric derivation. Never fed to the test generator alongside the prompt itself (that would be circular).
4. **Test data** — path to a `.jsonl` / `.yaml` test file, or `generate N` to synthesize tests, or a directory of pre-recorded input/output pairs.
5. **Source model** — a Bedrock model ID, or `openai:...` / `anthropic:...`, or `--baseline-from-tests`.

All artifacts are written to `./nova-migrate-runs/{timestamp}/` in the directory you invoked the skill from. The final `REPORT.md` contains the verdict and everything needed to audit the run.

### Test file format

JSONL (one test per line) or YAML. Full schema in [skills/nova-migrate/test_schema.md](skills/nova-migrate/test_schema.md). Minimal example:

```jsonl
{"id": "t1", "input": "...", "expected_behavior": "..."}
{"id": "t2", "input": "...", "expected_output": "..."}
```

Example test files in [skills/nova-migrate/examples/](skills/nova-migrate/examples/).

## What the skill won't do

- **Migrate multiple prompts at once.** Run the skill once per prompt — batching muddies the eval signal.
- **Invent test data from the prompt.** Synthetic tests are always generated from the task description, not the prompt.
- **Ship with unaddressed regressions.** If any test scores below baseline at the final iteration, the report verdict is "ship with caveats" or "do not ship", never a plain "ship".
- **Fork the prompting skills.** `/nova-migrate` always delegates optimization to `/nova1-prompt` or `/nova2-prompt`.

## Troubleshooting

- **"helper.py: command not found" / Python errors.** Ensure `uv` is installed and on `PATH`, and that you're invoking the skill from a directory where `uv run` works.
- **"NoCredentialsError" from boto3.** Run `aws configure` or set `AWS_PROFILE`. Confirm with `aws sts get-caller-identity`.
- **"OPENAI_API_KEY is not set"** (or similar). Export the env var, switch to a Bedrock source model, or use `--baseline-from-tests`.
- **All scores come back empty with a `parse_error` critique.** The judge model returned something that wasn't JSON. Lower the judge's `--concurrency` or switch `--judge-model` to a stronger Bedrock model.

## Status

- ✅ Skill orchestration logic and workflow defined
- ✅ Test file schema (JSONL + YAML)
- ✅ Plugin + install script wiring
- ✅ `helper.py` wired: Bedrock (boto3 Converse), OpenAI, Anthropic, parallel batching, LLM-as-judge scoring with JSON-tolerant parsing
- 🚧 Refine-loop logic is described in `SKILL.md` but end-to-end validation against real use cases is still pending — treat scores as directional until the workflow has been exercised on a few real migrations.
