"""
Amazon Nova Prompt Transformer

Simple API to align prompts with Amazon Nova guidelines.
"""

import os
import time
import glob
import boto3
from botocore.config import Config
from contextlib import contextmanager


# ============================================================================
# File utilities
# ============================================================================

def load_text_file(directory, filename):
    """Load a specific text file."""
    filepath = os.path.join(directory, filename)
    with open(filepath, 'r', encoding='utf-8') as file:
        return file.read()


def load_text_files(directory):
    """Load all text files from a directory into a dictionary."""
    files_dict = {}
    for filepath in glob.glob(os.path.join(directory, '*.txt')):
        filename = os.path.basename(filepath)
        filename_without_ext = os.path.splitext(filename)[0]
        with open(filepath, 'r', encoding='utf-8') as file:
            files_dict[filename_without_ext] = file.read()
    return files_dict


# ============================================================================
# Bedrock client utilities
# ============================================================================

def get_bedrock_client():
    """Create and configure a Bedrock client.

    Uses AWS_PROFILE environment variable if set.
    Region is automatically detected from AWS configuration.
    """
    config = Config(
        read_timeout=1000,
        max_pool_connections=1000
    )

    # AWS SDK automatically uses AWS_PROFILE and AWS_REGION env vars
    return boto3.client(
        service_name='bedrock-runtime',
        config=config
    )


@contextmanager
def bedrock_client_context():
    """Context manager for Bedrock client to ensure proper cleanup."""
    client = get_bedrock_client()
    try:
        yield client
    finally:
        client.close()


def bedrock_converse(bedrock_client, system_input, message, tool_list, model_id, inference_config=None):
    """Make a conversation request to Bedrock."""

    # Update tool choice if tools are provided
    if tool_list and 'tools' in tool_list and len(tool_list['tools']) > 0:
        tool_list.update({"toolChoice": {"tool": {"name": tool_list['tools'][0]['toolSpec']['name']}}})

    # Set default inference configuration if none provided
    if not inference_config:
        inference_config = {
            "maxTokens": 16000,
            # "temperature": 0.6,
            "topP": 0.4
        }

    try:
        response = bedrock_client.converse(
            modelId=model_id,
            system=[system_input],
            messages=[message],
            inferenceConfig=inference_config,
            toolConfig=tool_list
        )
        return response
    except bedrock_client.exceptions.ThrottlingException as e:
        wait_sec = 60
        print(f'LLM got throttled, waiting {str(wait_sec)} seconds.')
        # nosemgrep: arbitrary-sleep
        time.sleep(wait_sec)
        # Recursive retry
        return bedrock_converse(bedrock_client, system_input, message, tool_list, model_id, inference_config)


# ============================================================================
# Guidance loading utilities
# ============================================================================

# Base guidance files always loaded (core prompting best practices)
BASE_GUIDANCE_FILES = [
    "creating_precise_prompts",
    "bring_focus_to_sections",
    "system_role",
    "few_shot_prompting",
    "chain_of_thought_prompting",
    "requiring_structured_output",
]

# Mapping from intents to additional guidance files
INTENT_GUIDANCE_MAP = {
    "image_understanding": ["image_understanding"],
    "video_understanding": ["video_understanding"],
    "document_understanding": ["document_understanding"],
    "tool_use": ["tool_use"],
    "structured_output": ["requiring_structured_output"],  # Already in base, but explicit
    "rag": ["provide_supporting_text", "long_context"],
    "multilingual": ["multilingual"],
    "agentic": ["agentic", "tool_use", "reasoning_mode"],
}

GUIDANCE_DIR = os.path.join("data", "docs", "nova", "general")


def load_guidance_for_intents(intents=None):
    """Load guidance files based on identified intents.

    Args:
        intents (list, optional): List of intent strings. If None, loads all guidance.

    Returns:
        str: Combined guidance text from relevant files.
    """
    # Determine which files to load
    if intents is None:
        # Load all guidance files
        all_guidance = load_text_files(GUIDANCE_DIR)
        return "\n\n".join(all_guidance.values())

    # Start with base guidance files
    files_to_load = set(BASE_GUIDANCE_FILES)

    # Add intent-specific guidance
    for intent in intents:
        if intent in INTENT_GUIDANCE_MAP:
            files_to_load.update(INTENT_GUIDANCE_MAP[intent])

    # Load the files
    guidance_parts = []
    for filename in files_to_load:
        filepath = os.path.join(GUIDANCE_DIR, f"{filename}.txt")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                guidance_parts.append(f.read())

    return "\n\n".join(guidance_parts)


# ============================================================================
# Main transform function
# ============================================================================

def transform_prompt(prompt, model_id=None, intents=None):
    """Transform any prompt to align with Amazon Nova guidelines.

    Args:
        prompt (str): The prompt to transform
        model_id (str, optional): Model to use for transformation. Defaults to Nova Premier.
            Options:
            - 'us.amazon.nova-premier-v1:0' (default)
            - 'global.anthropic.claude-sonnet-4-5-20250929-v1:0'
        intents (list, optional): List of intents to load specific guidance for.
            If None, loads all guidance. Use classify_intent() to get intents.

    Returns:
        dict: Dictionary containing:
            - thinking: Analysis of the transformation process
            - nova_draft: Initial transformed prompt
            - reflection: Reflection on the draft
            - nova_final: Final Nova-aligned prompt

    Environment Variables:
        AWS_PROFILE: AWS profile to use (optional, will use default if not set)
        AWS_REGION: AWS region (optional, will use default if not set)

    Example:
        >>> result = transform_prompt("Summarize this document: {document}")
        >>> print(result['nova_final'])

        >>> # With intent-based guidance loading
        >>> intents = classify_intent(prompt)['intents']
        >>> result = transform_prompt(prompt, intents=intents)
    """

    # Default to Nova Premier if no model specified
    if model_id is None:
        model_id = 'us.amazon.nova-premier-v1:0'

    # Load required prompt files
    system_prompt = load_text_file(os.path.join("data", "prompts"), "prompt_nova_migration_system.txt")
    prompt_template = load_text_file(os.path.join("data", "prompts"), "prompt_nova_migration.txt")
    migration_guidelines = load_text_file(os.path.join("data", "docs", "nova"), "migration_guidelines.txt")

    # Load guidance based on intents (or all if no intents specified)
    nova_docs = load_guidance_for_intents(intents)

    # Format the prompt
    formatted_prompt = prompt_template.format(
        nova_docs=nova_docs,
        migration_guidelines=migration_guidelines,
        current_prompt=prompt,
    )

    # Define the tool for structured output
    tool_list = {
        "tools": [
            {
                "toolSpec": {
                    "name": "convert_prompt",
                    "description": "Transforms any prompt to Nova-aligned format",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "thinking": {
                                    "type": "string",
                                    "description": "Detailed analysis of the transformation process including model-specific elements, relevant documentation, required optimizations, Nova compatibility considerations, and format adjustments",
                                },
                                "nova_draft": {
                                    "type": "string",
                                    "description": "The transformed Nova-aligned prompt following best practices",
                                },
                                "reflection": {
                                    "type": "string",
                                    "description": "Reflection on the draft prompt",
                                },
                                "nova_final": {
                                    "type": "string",
                                    "description": "Final Nova-aligned prompt based on reflections",
                                },
                            },
                            "required": [
                                "thinking",
                                "nova_draft",
                                "reflection",
                                "nova_final",
                            ],
                        }
                    },
                }
            }
        ]
    }

    system_message = {"text": system_prompt}
    message = {
        "role": "user",
        "content": [{"text": formatted_prompt}],
    }

    # Execute the transformation
    with bedrock_client_context() as client:
        response = bedrock_converse(client, system_message, message, tool_list, model_id)

    return response["output"]["message"]["content"][0]["toolUse"]["input"]


# ============================================================================
# Intent classification
# ============================================================================

# Valid intents for classification
VALID_INTENTS = [
    "image_understanding",
    "video_understanding",
    "document_understanding",
    "tool_use",
    "structured_output",
    "rag",
    "multilingual",
    "agentic",
]


def classify_intent(prompt, model_id=None):
    """Classify a prompt to identify required capabilities and modalities.

    Args:
        prompt (str): The prompt to classify
        model_id (str, optional): Model to use for classification. Defaults to Nova Micro.
            Options:
            - 'us.amazon.nova-micro-v1:0' (default)
            - 'us.amazon.nova-lite-v1:0'
            - 'us.amazon.nova-premier-v1:0'

    Returns:
        dict: Dictionary containing:
            - intents: List of identified intents from the taxonomy
            - reasoning: Explanation of why each intent was identified

    Environment Variables:
        AWS_PROFILE: AWS profile to use (optional, will use default if not set)
        AWS_REGION: AWS region (optional, will use default if not set)

    Example:
        >>> result = classify_intent("Analyze this image and return JSON: {image}")
        >>> print(result['intents'])
        ['image_understanding', 'structured_output']
    """

    # Default to Nova Micro for fast, cheap classification
    if model_id is None:
        model_id = 'us.amazon.nova-micro-v1:0'

    # Load required prompt files
    system_prompt = load_text_file(os.path.join("data", "prompts"), "prompt_intent_classifier_system.txt")
    prompt_template = load_text_file(os.path.join("data", "prompts"), "prompt_intent_classifier.txt")

    # Format the prompt
    formatted_prompt = prompt_template.format(input_prompt=prompt)

    # Define the tool for structured output
    tool_list = {
        "tools": [
            {
                "toolSpec": {
                    "name": "classify_intents",
                    "description": "Classifies a prompt into applicable intents from the taxonomy",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "reasoning": {
                                    "type": "string",
                                    "description": "Explanation of the classification reasoning, noting signals found for each identified intent",
                                },
                                "intents": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": VALID_INTENTS,
                                    },
                                    "description": "List of identified intents from the taxonomy",
                                },
                            },
                            "required": ["reasoning", "intents"],
                        }
                    },
                }
            }
        ]
    }

    system_message = {"text": system_prompt}
    message = {
        "role": "user",
        "content": [{"text": formatted_prompt}],
    }

    # Use lower token limit for classification
    inference_config = {
        "maxTokens": 1024,
        "topP": 0.4
    }

    # Execute the classification
    with bedrock_client_context() as client:
        response = bedrock_converse(client, system_message, message, tool_list, model_id, inference_config)

    return response["output"]["message"]["content"][0]["toolUse"]["input"]


# ============================================================================
# Combined pipeline
# ============================================================================

def transform_with_intent_classification(prompt, classifier_model_id=None, transform_model_id=None):
    """Transform a prompt using intent-based guidance selection.

    This is the main entry point that chains:
    1. Intent classification (fast, using Nova Micro)
    2. Guidance loading (based on detected intents)
    3. Prompt transformation (using Nova Premier or specified model)

    Args:
        prompt (str): The prompt to transform
        classifier_model_id (str, optional): Model for intent classification.
            Defaults to 'us.amazon.nova-micro-v1:0'
        transform_model_id (str, optional): Model for transformation.
            Defaults to 'us.amazon.nova-premier-v1:0'

    Returns:
        dict: Dictionary containing:
            - intents: List of detected intents
            - intent_reasoning: Explanation of intent classification
            - thinking: Analysis of the transformation process
            - nova_draft: Initial transformed prompt
            - reflection: Reflection on the draft
            - nova_final: Final Nova-aligned prompt
            - guidance_files: List of guidance files that were loaded

    Example:
        >>> result = transform_with_intent_classification(
        ...     "Analyze this image and return JSON: {image}"
        ... )
        >>> print(f"Detected intents: {result['intents']}")
        >>> print(f"Optimized prompt: {result['nova_final']}")
    """

    # Step 1: Classify intent
    intent_result = classify_intent(prompt, model_id=classifier_model_id)
    intents = intent_result.get('intents', [])

    # Step 2: Determine which guidance files will be loaded
    files_to_load = set(BASE_GUIDANCE_FILES)
    for intent in intents:
        if intent in INTENT_GUIDANCE_MAP:
            files_to_load.update(INTENT_GUIDANCE_MAP[intent])

    # Step 3: Transform with intent-specific guidance
    transform_result = transform_prompt(
        prompt,
        model_id=transform_model_id,
        intents=intents
    )

    # Combine results
    return {
        'intents': intents,
        'intent_reasoning': intent_result.get('reasoning', ''),
        'guidance_files': sorted(list(files_to_load)),
        **transform_result
    }


# ============================================================================
# Example usage
# ============================================================================

if __name__ == "__main__":
    # Example: Full pipeline with intent classification
    current_prompt = "Analyze this image and return a JSON object with detected objects: {image}"

    print("=" * 80)
    print("INPUT PROMPT:")
    print("=" * 80)
    print(current_prompt)

    print("\n" + "=" * 80)
    print("RUNNING FULL PIPELINE:")
    print("=" * 80)

    result = transform_with_intent_classification(current_prompt)

    print(f"\nDetected Intents: {result['intents']}")
    print(f"Intent Reasoning: {result['intent_reasoning']}")
    print(f"Guidance Files Loaded: {result['guidance_files']}")

    print("\n" + "=" * 80)
    print("FINAL NOVA-ALIGNED PROMPT:")
    print("=" * 80)
    print(result['nova_final'])
