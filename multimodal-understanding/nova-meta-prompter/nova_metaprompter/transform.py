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
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


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


def bedrock_converse(bedrock_client, system_input, message, tool_list, model_id, inference_config=None, addtional_model_request_fields=None):
    """Make a conversation request to Bedrock."""

    # # Update tool choice if tools are provided
    # if tool_list and 'tools' in tool_list and len(tool_list['tools']) > 0:
    #     tool_list.update({"toolChoice": {"tool": {"name": tool_list['tools'][0]['toolSpec']['name']}}})

    # Set default inference configuration if none provided
    if not inference_config:
        inference_config = {
            "maxTokens": 10000,
            "topP": 0.9,
            "temperature": 1
        }

    if not addtional_model_request_fields:
        addtional_model_request_fields = {

        }

    try:
        response = bedrock_client.converse(
            modelId=model_id,
            system=[system_input],
            messages=[message],
            inferenceConfig=inference_config,
            toolConfig=tool_list,
            additionalModelRequestFields=addtional_model_request_fields
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
]

# Mapping from intents to additional guidance files
INTENT_GUIDANCE_MAP = {
    "text_understanding": [],
    "image_understanding": ["image_understanding"],
    "video_understanding": ["video_understanding"],
    "document_understanding": ["document_understanding"],
    "tool_use": ["tool_use"],
    "structured_output": ["requiring_structured_output"],
    "rag": ["provide_supporting_text", "long_context"],
    "multilingual": ["multilingual"],
    "agentic": ["agentic", "tool_use", "reasoning_mode"],
}

GUIDANCE_DIR = os.path.join(DATA_DIR, "docs", "nova", "general")

# Mapping from boolean flag names to guidance files
API_CAPABILITY_GUIDANCE = {
    "reasoning_mode": ["reasoning_mode"],
    "tool_use": ["tool_use"],
    "image": ["image_understanding"],
    "video": ["video_understanding"],
}


def load_guidance_for_intents(intents=None, reasoning_mode=False, tool_use=False,
                               image=False, video=False):
    """Load guidance files based on identified intents and API capabilities.

    Args:
        intents (list, optional): List of intent strings. If None, loads all guidance.
        reasoning_mode (bool): Enable reasoning mode guidance.
        tool_use (bool): Enable tool use guidance.
        image (bool): Enable image understanding guidance.
        video (bool): Enable video understanding guidance.

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

    # Add API capability-specific guidance
    api_flags = {
        "reasoning_mode": reasoning_mode,
        "tool_use": tool_use,
        "image": image,
        "video": video,
    }
    for capability, enabled in api_flags.items():
        if enabled and capability in API_CAPABILITY_GUIDANCE:
            files_to_load.update(API_CAPABILITY_GUIDANCE[capability])

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

def transform_prompt(prompt, model_id=None, intents=None,
                     reasoning_mode=False, tool_use=False, image=False, video=False):
    """Transform any prompt to align with Amazon Nova guidelines.

    Args:
        prompt (str): The prompt to transform
        model_id (str, optional): Model to use for transformation. Defaults to Nova Premier.
            Options:
            - 'us.amazon.nova-premier-v1:0' (default)
            - 'global.anthropic.claude-sonnet-4-5-20250929-v1:0'
        intents (list, optional): List of intents to load specific guidance for.
            If None, loads all guidance. Use classify_intent() to get intents.
        reasoning_mode (bool): Enable reasoning mode guidance for API-level reasoning.
        tool_use (bool): Enable tool use guidance for API-level tool definitions.
        image (bool): Enable image understanding guidance for image inputs.
        video (bool): Enable video understanding guidance for video inputs.

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

        >>> # With API capability flags
        >>> result = transform_prompt(prompt, reasoning_mode=True, image=True)
    """

    # Default to Nova Premier if no model specified
    if model_id is None:
        model_id = 'us.amazon.nova-2-pro-preview-20251202-v1:0'

    # Load required prompt files
    system_prompt = load_text_file(os.path.join(DATA_DIR, "prompts"), "prompt_nova_migration_system.txt")
    prompt_template = load_text_file(os.path.join(DATA_DIR, "prompts"), "prompt_nova_migration.txt")
    migration_guidelines = load_text_file(os.path.join(DATA_DIR, "docs", "nova"), "migration_guidelines.txt")

    # Load guidance based on intents and API capabilities
    nova_docs = load_guidance_for_intents(
        intents,
        reasoning_mode=reasoning_mode,
        tool_use=tool_use,
        image=image,
        video=video
    )

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
                                "steps": {
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
                                "steps",
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
        response = bedrock_converse(client, system_message, message, tool_list, model_id, addtional_model_request_fields={"inferenceConfig": {"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}}})

    content_list = response["output"]["message"]["content"]
    tool_call = next((item for item in content_list if "toolUse" in item), None)

    return tool_call["toolUse"]["input"]


# ============================================================================
# Intent classification
# ============================================================================

# Valid intents for classification
VALID_INTENTS = [
    "text_understanding",
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
        model_id = 'us.amazon.nova-2-lite-v1:0'

    # Load required prompt files
    system_prompt = load_text_file(os.path.join(DATA_DIR, "prompts"), "prompt_intent_classifier_system.txt")
    prompt_template = load_text_file(os.path.join(DATA_DIR, "prompts"), "prompt_intent_classifier.txt")

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

def transform_with_intent_classification(prompt, n=4, classifier_model_id=None,
                                          transform_model_id=None, judge_model_id=None,
                                          reasoning_mode=False, tool_use=False,
                                          image=False, video=False, max_workers=None):
    """Transform a prompt using intent-based guidance selection with best-of-N judging.

    This is the main entry point that chains:
    1. Intent classification (fast, using Nova Lite)
    2. Guidance loading (based on detected intents + API capabilities)
    3. N candidate prompt transformations in parallel
    4. Judge selects the best candidate (when N > 1)

    Args:
        prompt (str): The prompt to transform
        n (int): Number of candidate transformations to generate. Defaults to 4.
            Set to 1 to skip candidate generation and judging.
        classifier_model_id (str, optional): Model for intent classification.
            Defaults to 'us.amazon.nova-2-lite-v1:0'
        transform_model_id (str, optional): Model for transformation.
            Defaults to 'us.amazon.nova-2-pro-preview-20251202-v1:0'
        judge_model_id (str, optional): Model for judging candidates.
            Defaults to 'us.amazon.nova-2-pro-preview-20251202-v1:0'
        reasoning_mode (bool): Enable reasoning mode guidance for API-level reasoning.
        tool_use (bool): Enable tool use guidance for API-level tool definitions.
        image (bool): Enable image understanding guidance for image inputs.
        video (bool): Enable video understanding guidance for video inputs.
        max_workers (int, optional): Max parallel threads for candidate generation.
            Defaults to n.

    Returns:
        dict: Dictionary containing:
            - intents: List of detected intents
            - intent_reasoning: Explanation of intent classification
            - api_capabilities: Dict of explicitly enabled API capabilities
            - guidance_files: List of guidance files that were loaded
            - steps: Analysis of the transformation process
            - nova_draft: Initial transformed prompt
            - reflection: Reflection on the draft
            - nova_final: Final Nova-aligned prompt
            When n > 1, also includes:
            - judge_reasoning: Explanation of why the winner was selected
            - judge_evaluations: List of per-candidate evaluation dicts
            - selected_candidate_id: 1-indexed ID of the winning candidate
            - all_candidates: List of all N results for inspection

    Raises:
        RuntimeError: If all N transformation attempts fail (when n > 1).

    Example:
        >>> # Default: 4 candidates + judge
        >>> result = transform_with_intent_classification(
        ...     "Analyze this image and return JSON: {image}"
        ... )
        >>> print(f"Detected intents: {result['intents']}")
        >>> print(f"Optimized prompt: {result['nova_final']}")

        >>> # Single candidate (no judge)
        >>> result = transform_with_intent_classification(
        ...     "Summarize this document", n=1
        ... )

        >>> # With API capability flags
        >>> result = transform_with_intent_classification(
        ...     "Analyze the chart and recommend next steps",
        ...     reasoning_mode=True,
        ...     image=True
        ... )
    """
    if max_workers is None:
        max_workers = n

    # Step 1: Classify intent
    intent_result = classify_intent(prompt, model_id=classifier_model_id)
    intents = intent_result.get('intents', [])

    # Step 2: Determine which guidance files will be loaded
    files_to_load = set(BASE_GUIDANCE_FILES)
    for intent in intents:
        if intent in INTENT_GUIDANCE_MAP:
            files_to_load.update(INTENT_GUIDANCE_MAP[intent])

    # Add API capability-specific guidance files
    api_capabilities = {
        "reasoning_mode": reasoning_mode,
        "tool_use": tool_use,
        "image": image,
        "video": video,
    }
    for capability, enabled in api_capabilities.items():
        if enabled and capability in API_CAPABILITY_GUIDANCE:
            files_to_load.update(API_CAPABILITY_GUIDANCE[capability])

    metadata = {
        'intents': intents,
        'intent_reasoning': intent_result.get('reasoning', ''),
        'api_capabilities': api_capabilities,
        'guidance_files': sorted(list(files_to_load)),
    }

    transform_kwargs = dict(
        model_id=transform_model_id,
        intents=intents,
        reasoning_mode=reasoning_mode,
        tool_use=tool_use,
        image=image,
        video=video,
    )

    # Step 3: Single candidate path (no judge)
    if n <= 1:
        transform_result = transform_prompt(prompt, **transform_kwargs)
        return {**metadata, **transform_result}

    # Step 4: Generate N candidates in parallel
    def _run_transform(_i):
        return transform_prompt(prompt, **transform_kwargs)

    candidates = []
    errors = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_transform, i): i for i in range(n)}
        for future in as_completed(futures):
            try:
                result = future.result()
                candidates.append(result)
            except Exception as e:
                errors.append(e)

    if len(candidates) == 0:
        raise RuntimeError(
            f"All {n} transformation attempts failed. Errors: {errors}"
        )

    if len(candidates) == 1:
        # Only one survived — skip judge
        return {
            **metadata,
            **candidates[0],
            'judge_reasoning': 'Only one candidate succeeded; judge was skipped.',
            'judge_evaluations': [],
            'selected_candidate_id': 1,
            'all_candidates': candidates,
        }

    # Step 5: Judge picks the best candidate
    judge_result = _judge_candidates(prompt, candidates, model_id=judge_model_id)

    selected_id = judge_result['selected_candidate_id']
    selected_id = max(1, min(selected_id, len(candidates)))
    winner = candidates[selected_id - 1]

    return {
        **metadata,
        **winner,
        'judge_reasoning': judge_result.get('reasoning', ''),
        'judge_evaluations': judge_result.get('evaluations', []),
        'selected_candidate_id': selected_id,
        'all_candidates': candidates,
    }


# ============================================================================
# Best-of-N with judge
# ============================================================================

def _judge_candidates(original_prompt, candidates, model_id=None):
    """Judge multiple transformation candidates and select the best one.

    Args:
        original_prompt (str): The original prompt that was transformed.
        candidates (list): List of candidate result dicts, each containing 'nova_final'.
        model_id (str, optional): Model to use for judging. Defaults to Nova Premier.

    Returns:
        dict: Dictionary containing:
            - evaluations: List of per-candidate evaluation dicts
            - reasoning: Explanation of why the winner was selected
            - selected_candidate_id: 1-indexed ID of the winning candidate
    """
    if model_id is None:
        model_id = 'us.amazon.nova-2-pro-preview-20251202-v1:0'

    # Load judge prompt templates
    system_prompt = load_text_file(os.path.join(DATA_DIR, "prompts"), "prompt_judge_system.txt")
    prompt_template = load_text_file(os.path.join(DATA_DIR, "prompts"), "prompt_judge.txt")
    migration_guidelines = load_text_file(os.path.join(DATA_DIR, "docs", "nova"), "migration_guidelines.txt")

    # Format candidates as XML blocks
    candidate_blocks = []
    for i, candidate in enumerate(candidates, 1):
        candidate_blocks.append(f'<candidate id="{i}">\n{candidate["nova_final"]}\n</candidate>')
    candidates_xml = "\n\n".join(candidate_blocks)

    # Format the judge prompt
    formatted_prompt = prompt_template.format(
        original_prompt=original_prompt,
        migration_guidelines=migration_guidelines,
        candidates_xml=candidates_xml,
        n=len(candidates),
    )

    # Define binary metric properties for the tool schema
    binary_metrics = [
        "preserves_all_variables",
        "preserves_constraints",
        "preserves_examples",
        "preserves_output_format",
        "preserves_business_logic",
        "uses_section_headers",
        "follows_migration_guidelines",
        "removes_source_model_artifacts",
        "clear_instruction_flow",
        "no_redundancy",
    ]

    metric_properties = {}
    for metric in binary_metrics:
        metric_properties[metric] = {
            "type": "integer",
            "description": f"Binary score (0 or 1) for {metric}",
        }
    metric_properties["total_score"] = {
        "type": "integer",
        "description": "Sum of all binary metrics (0-10)",
    }

    tool_list = {
        "tools": [
            {
                "toolSpec": {
                    "name": "select_best_candidate",
                    "description": "Evaluate candidates and select the best one",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "evaluations": {
                                    "type": "array",
                                    "description": "One evaluation per candidate",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "candidate_id": {
                                                "type": "integer",
                                                "description": "1-indexed candidate ID",
                                            },
                                            **metric_properties,
                                        },
                                        "required": ["candidate_id", *binary_metrics, "total_score"],
                                    },
                                },
                                "reasoning": {
                                    "type": "string",
                                    "description": "Explanation of why the winner is best and key differences between top candidates",
                                },
                                "selected_candidate_id": {
                                    "type": "integer",
                                    "description": "1-indexed ID of the best candidate",
                                },
                            },
                            "required": ["evaluations", "reasoning", "selected_candidate_id"],
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

    # Lower temperature for consistent judging
    inference_config = {
        "maxTokens": 4096,
        "topP": 0.9,
        "temperature": 0.3,
    }

    with bedrock_client_context() as client:
        response = bedrock_converse(client, system_message, message, tool_list, model_id, inference_config)

    content_list = response["output"]["message"]["content"]
    tool_call = next((item for item in content_list if "toolUse" in item), None)

    return tool_call["toolUse"]["input"]


def transform_prompt_best_of_n(prompt, n=4, classifier_model_id=None,
                                transform_model_id=None, judge_model_id=None,
                                reasoning_mode=False, tool_use=False,
                                image=False, video=False, max_workers=None):
    """Generate N prompt transformations in parallel and use a judge to pick the best.

    This is a convenience alias for transform_with_intent_classification().

    Args:
        prompt (str): The prompt to transform.
        n (int): Number of candidate transformations to generate. Defaults to 4.
        classifier_model_id (str, optional): Model for intent classification.
        transform_model_id (str, optional): Model for transformation.
        judge_model_id (str, optional): Model for judging candidates.
        reasoning_mode (bool): Enable reasoning mode guidance.
        tool_use (bool): Enable tool use guidance.
        image (bool): Enable image understanding guidance.
        video (bool): Enable video understanding guidance.
        max_workers (int, optional): Max parallel threads. Defaults to n.

    Returns:
        dict: See transform_with_intent_classification() for full return schema.

    Raises:
        RuntimeError: If all N transformation attempts fail.
    """
    return transform_with_intent_classification(
        prompt,
        n=n,
        classifier_model_id=classifier_model_id,
        transform_model_id=transform_model_id,
        judge_model_id=judge_model_id,
        reasoning_mode=reasoning_mode,
        tool_use=tool_use,
        image=image,
        video=video,
        max_workers=max_workers,
    )


# ============================================================================
# Example usage
# ============================================================================

if __name__ == "__main__":
    # Example: Full pipeline with intent classification, best-of-4 candidates, and judge
    current_prompt = "Analyze the chart and recommend investment strategies"

    print("=" * 80)
    print("INPUT PROMPT:")
    print("=" * 80)
    print(current_prompt)

    print("\n" + "=" * 80)
    print("RUNNING FULL PIPELINE (4 candidates + judge):")
    print("  - reasoning_mode=True (for complex analysis)")
    print("  - image=True (chart will be passed via API)")
    print("=" * 80)

    result = transform_with_intent_classification(
        current_prompt,
        reasoning_mode=True,
        image=True
    )

    print(f"\nDetected Intents: {result['intents']}")
    print(f"Intent Reasoning: {result['intent_reasoning']}")
    print(f"API Capabilities: {result['api_capabilities']}")
    print(f"Guidance Files Loaded: {result['guidance_files']}")
    print(f"Selected Candidate: {result.get('selected_candidate_id', 'N/A')}")
    print(f"Judge Reasoning: {result.get('judge_reasoning', 'N/A')}")

    print("\n" + "=" * 80)
    print("FINAL NOVA-ALIGNED PROMPT:")
    print("=" * 80)
    print(result['nova_final'])
