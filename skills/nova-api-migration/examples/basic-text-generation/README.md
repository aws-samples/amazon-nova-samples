# Example: Basic Text Generation Migration

Demonstrates migrating a simple text generation call from each provider to Nova 2 Lite.

## What Changed

| Aspect | Gemini | OpenAI | Claude | Nova 2 Lite |
|--------|--------|--------|--------|-------------|
| SDK | `google-genai` | `openai` | `anthropic` | `boto3` |
| Auth | API key | API key | API key | AWS IAM |
| System prompt | `system_instruction=` | Message with `role: system` | Top-level `system=` | `system=[{"text":...}]` |
| Content format | Parts | String | String/blocks | Typed blocks |
| Inference params | `GenerateContentConfig` | Top-level kwargs | Top-level kwargs | Nested `inferenceConfig` |

## Input (before)

See each provider's `before_*.py` file.

## Output (after)

See `after_nova.py` — identical regardless of source provider.
