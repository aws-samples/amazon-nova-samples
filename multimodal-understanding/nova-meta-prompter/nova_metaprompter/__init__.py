"""
Nova Meta Prompter - Transform prompts to align with Amazon Nova guidelines.

Usage:
    from nova_metaprompter import transform_prompt

    result = transform_prompt("Your prompt here")
    print(result['nova_final'])

For batch processing, use the batch_transform submodule:
    from nova_metaprompter.batch_transform import load_prompts, save_results, transform_single

Or run from the command line:
    python -m nova_metaprompter.batch_transform input.jsonl -o output.jsonl
    nova-metaprompter-batch input.jsonl -o output.jsonl
"""

from nova_metaprompter.transform import (
    transform_with_intent_classification as transform_prompt,
    VALID_INTENTS,
)

__all__ = [
    "transform_prompt",
    "VALID_INTENTS",
]
