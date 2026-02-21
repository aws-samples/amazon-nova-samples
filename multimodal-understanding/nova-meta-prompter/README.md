# Amazon Nova Meta Prompter

Transform prompts to align with Amazon Nova guidelines using an automated 3-step pipeline:

1. **Intent Classification** -- Detects what your prompt needs (image understanding, RAG, tool use, etc.)
2. **Targeted Guidance Loading** -- Loads only the relevant Nova best-practice documents for detected intents
3. **Prompt Transformation** -- Rewrites your prompt following Nova guidelines, with analysis, draft, reflection, and final output

## Installation

```bash
pip install -e .

# If you want to use the interactive notebook:
pip install -e ".[notebook]"
```

## AWS Configuration

Requires AWS credentials with Amazon Bedrock access:

```bash
export AWS_PROFILE=your-profile-name
export AWS_REGION=us-west-2
```

## Quick Start

### Python API

```python
from nova_metaprompter import transform_prompt

result = transform_prompt(
    "Analyze this image and return a JSON object with all detected objects, "
    "their locations, and confidence scores."
)

# Detected intents (e.g. ['image_understanding', 'structured_output'])
print(result['intents'])

# The transformed prompt
print(result['nova_final'])
```

`transform_prompt` classifies your prompt's intents, loads relevant guidance, generates multiple candidate transformations, and uses a judge to pick the best one.

### Interactive Notebook

```bash
jupyter notebook nova_metaprompter_showcase.ipynb
```

The notebook walks through intent classification, transformation examples by intent type, and a try-your-own cell.

### Batch Transform (CLI)

Transform many prompts at once from a JSONL, JSON, or text file:

```bash
# From a JSONL file (one {"prompt": "..."} per line)
python -m nova_metaprompter.batch_transform prompts.jsonl -o results.jsonl

# Or use the installed entry point
nova-metaprompter-batch prompts.jsonl -o results.json

# Fewer candidates for faster processing
nova-metaprompter-batch prompts.jsonl -o results.json --candidates 1

# Parallel processing
nova-metaprompter-batch prompts.jsonl -o results.json --workers 4

# Enable API capability flags
nova-metaprompter-batch prompts.jsonl -o results.json --image --reasoning-mode
```

See `examples/sample_prompts.jsonl` for example input format.

## API Reference

```python
from nova_metaprompter import transform_prompt

# Classifies intents, loads guidance, generates candidates, judges best one
result = transform_prompt("Your prompt here")
result['intents']       # e.g. ['image_understanding', 'structured_output']
result['nova_final']    # The transformed prompt
result['nova_draft']    # Initial draft before reflection
result['thinking']      # Model's analysis reasoning
result['reflection']    # Self-critique and improvements

# With API capability flags (for features you know you'll use)
result = transform_prompt(
    "Analyze the chart and recommend next steps",
    reasoning_mode=True,  # Include Nova reasoning mode guidance
    image=True,           # Include image understanding guidance
)
```

## Available Models

| Role | Default Model | Purpose |
|------|--------------|---------|
| Transform | `us.anthropic.claude-sonnet-4-6` | Prompt rewriting with adaptive reasoning |
| Judge | `us.anthropic.claude-sonnet-4-6` | Selecting best candidate from N transforms |
| Classifier | `us.amazon.nova-2-lite-v1:0` | Intent classification |

Override via function parameters (`transform_model_id`, `judge_model_id`, `classifier_model_id`) or CLI flags (`--model-id`, `--judge-model-id`, `--classifier-model-id`).

## Project Structure

```
nova-meta-prompter/
├── nova_metaprompter/
│   ├── __init__.py                # Package exports
│   ├── transform.py               # Core transformation and classification logic
│   ├── batch_transform.py         # Batch CLI for processing multiple prompts
│   └── data/
│       ├── prompts/               # System/user prompt templates
│       │   ├── prompt_nova_migration*.txt
│       │   ├── prompt_intent_classifier*.txt
│       │   └── prompt_judge*.txt
│       └── docs/nova/
│           ├── migration_guidelines.txt
│           └── general/           # Per-intent guidance files (CoT, tool use, etc.)
├── examples/
│   └── sample_prompts.jsonl       # Example batch input
├── nova_metaprompter_showcase.ipynb  # Interactive notebook
├── pyproject.toml
└── README.md
```

## Requirements

- Python 3.12+
- AWS credentials with Amazon Bedrock access
- Model access enabled for Claude Sonnet 4.6 and Nova Lite in your region
