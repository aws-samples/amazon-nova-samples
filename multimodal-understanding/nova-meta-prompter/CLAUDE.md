# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nova Meta Prompter transforms prompts to align with Amazon Nova guidelines. It uses Amazon Bedrock models (Nova Premier or Claude Sonnet) to analyze prompts and rewrite them following Nova best practices.

## Commands

```bash
# Install dependencies
pip install -e .

# Run transformation from command line
python transform.py

# Launch interactive notebook
jupyter notebook nova_metaprompter_showcase.ipynb
```

## AWS Configuration

Requires AWS credentials with Bedrock access:
```bash
export AWS_PROFILE=your-profile-name
export AWS_REGION=us-west-2
```

## Architecture

**transform.py** - Single-file implementation containing:
- `transform_prompt(prompt, model_id=None)` - Main API entry point
- `bedrock_converse()` - Handles Bedrock API calls with throttling retry
- `get_bedrock_client()` - Creates configured boto3 client

**Transformation flow:**
1. Load system prompt and template from `data/prompts/`
2. Load Nova documentation from `data/docs/nova/` and `data/nova/general/`
3. Format prompt with guidelines
4. Call Bedrock Converse API with tool use for structured output
5. Return dict with: `thinking`, `nova_draft`, `reflection`, `nova_final`

**Data files:**
- `data/prompts/` - System and user prompt templates
- `data/docs/nova/migration_guidelines.txt` - Migration reference
- `data/docs/nova/general/` - Nova prompting best practices (few-shot, CoT, structured output, etc.)

## Supported Models

- `us.amazon.nova-premier-v1:0` (default)
- `global.anthropic.claude-sonnet-4-5-20250929-v1:0`
