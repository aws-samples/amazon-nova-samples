"""
Amazon Nova Prompt Transformer

Simple API to align prompts with Amazon Nova guidelines.
"""

import os
import re
import time
import random
import glob
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ============================================================================
# Default model IDs
# ============================================================================

DEFAULT_CLASSIFIER_MODEL_ID = "us.amazon.nova-2-lite-v1:0"
DEFAULT_TRANSFORM_MODEL_ID = "us.anthropic.claude-sonnet-4-6"
DEFAULT_JUDGE_MODEL_ID = "openai.gpt-oss-20b-1:0"


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


def parse_xml_tag(text, tag, strict=False):
    """Extract content between <tag>...</tag>.

    Args:
        text: Source text to parse.
        tag: XML tag name to look for.
        strict: If True, raise ValueError when multiple matches are found.

    Returns:
        Last match (stripped) or None if no match found.

    Raises:
        ValueError: If strict=True and multiple matches are found.
    """
    matches = re.findall(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    if strict and len(matches) > 1:
        raise ValueError(
            f"Expected exactly one <{tag}> tag but found {len(matches)}"
        )
    return matches[-1].strip() if matches else None


def parse_xml_tags(text, tag):
    """Extract all occurrences of <tag>...</tag>. Returns list of strings."""
    return [m.strip() for m in re.findall(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)]


def _extract_text(response):
    """Extract text content from Bedrock converse response."""
    content_list = response["output"]["message"]["content"]
    text_item = next((item for item in content_list if "text" in item), None)
    if text_item is None:
        raise ValueError(f"No text content in response. Content keys: "
                         f"{[list(item.keys()) for item in content_list]}")
    return text_item["text"]


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


def bedrock_converse(bedrock_client, system_input, message, model_id,
                     inference_config=None, additional_model_request_fields=None,
                     max_retries=5, base_delay=2):
    """Make a conversation request to Bedrock with bounded exponential backoff.

    Retries on ThrottlingException and ServiceUnavailableException up to
    max_retries times with exponential backoff and jitter.

    Args:
        bedrock_client: Boto3 Bedrock runtime client.
        system_input: System message dict.
        message: User message dict.
        model_id: Bedrock model identifier.
        inference_config: Optional inference configuration dict.
        additional_model_request_fields: Optional additional model request fields.
        max_retries: Maximum number of retry attempts (default 5).
        base_delay: Base delay in seconds for exponential backoff (default 2).
    """

    if not additional_model_request_fields:
        additional_model_request_fields = {}

    # Nova 2 with high reasoning effort does not support inferenceConfig
    # parameters (maxTokens, topP, temperature).
    reasoning_cfg = (additional_model_request_fields
                     .get("inferenceConfig", {})
                     .get("reasoningConfig", {}))
    is_nova2_high_reasoning = (
        "amazon.nova-2" in model_id
        and reasoning_cfg.get("maxReasoningEffort") == "high"
    )

    # Claude with extended thinking requires temperature=1.
    is_claude_thinking = (
        "anthropic.claude" in model_id
        and additional_model_request_fields.get("thinking", {}).get("type") == "enabled"
    )

    # Set default inference configuration if none provided,
    # unless Nova 2 high reasoning or Claude thinking prohibit certain params.
    if not inference_config and not is_nova2_high_reasoning:
        if is_claude_thinking:
            # Claude thinking requires temperature=1, topP >= 0.95 or unset,
            # and maxTokens > budget_tokens.
            inference_config = {"maxTokens": 16000, "temperature": 1}
        else:
            inference_config = {"maxTokens": 10000, "topP": 0.9, "temperature": 1}

    retryable_error_codes = {"ThrottlingException", "ServiceUnavailableException"}

    for attempt in range(max_retries + 1):
        try:
            converse_kwargs = dict(
                modelId=model_id,
                system=[system_input],
                messages=[message],
                additionalModelRequestFields=additional_model_request_fields,
            )
            if inference_config:
                converse_kwargs["inferenceConfig"] = inference_config

            response = bedrock_client.converse(**converse_kwargs)
            return response
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code not in retryable_error_codes:
                raise
            if attempt == max_retries:
                raise
            # Exponential backoff with full jitter
            delay = min(base_delay * (2 ** attempt), 120)
            jittered_delay = random.uniform(0, delay)  # nosemgrep: arbitrary-sleep
            print(f"Bedrock {error_code} (attempt {attempt + 1}/{max_retries}), "
                  f"retrying in {jittered_delay:.1f}s...")
            time.sleep(jittered_delay)


# ============================================================================
# XML output format instructions
# ============================================================================

OUTPUT_FORMAT_TRANSFORM = """

Respond using the following XML format. Do not include any text outside of the <response> tags.

<response>
<steps>Detailed analysis of the transformation process including model-specific elements, relevant documentation, required optimizations, Nova compatibility considerations, and format adjustments</steps>
<nova_draft>The transformed Nova-aligned prompt following best practices</nova_draft>
<reflection>Reflection on the draft prompt</reflection>
<nova_final>Final Nova-aligned prompt based on reflections</nova_final>
</response>
"""

OUTPUT_FORMAT_CLASSIFY = """

Respond using the following XML format. Do not include any text outside of the <response> tags.

Valid intent values: {valid_intents}

<response>
<reasoning>Explanation of the classification reasoning, noting signals found for each identified intent</reasoning>
<intents>
<intent>intent_name</intent>
</intents>
</response>
"""

OUTPUT_FORMAT_JUDGE = """

Respond using the following XML format. Do not include any text outside of the <response> tags.

<response>
<evaluations>
<evaluation>
<candidate_id>1-indexed candidate ID</candidate_id>
{metric_tags}
<total_score>Sum of all binary metrics (0-10)</total_score>
</evaluation>
</evaluations>
<reasoning>Explanation of why the winner is best and key differences between top candidates</reasoning>
<selected_candidate_id>1-indexed ID of the best candidate</selected_candidate_id>
</response>
"""


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
        return "\n\n".join(v for _, v in sorted(all_guidance.items()))

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
    for filename in sorted(files_to_load):
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
        model_id (str, optional): Model to use for transformation.
            Defaults to DEFAULT_TRANSFORM_MODEL_ID ('us.anthropic.claude-sonnet-4-6').
            Adaptive reasoning (extended thinking) is enabled automatically
            for Claude models.
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

    if model_id is None:
        model_id = DEFAULT_TRANSFORM_MODEL_ID

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

    # Format the prompt with XML output instructions
    formatted_prompt = prompt_template.format(
        nova_docs=nova_docs,
        migration_guidelines=migration_guidelines,
        current_prompt=prompt,
    )
    formatted_prompt += OUTPUT_FORMAT_TRANSFORM

    system_message = {"text": system_prompt}
    message = {
        "role": "user",
        "content": [{"text": formatted_prompt}],
    }

    # Model-specific reasoning configuration passed via
    # additionalModelRequestFields, not the top-level inferenceConfig.
    additional_fields = {}
    if "amazon.nova-2" in model_id:
        additional_fields = {"inferenceConfig": {"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "high"}}}
    elif "anthropic.claude" in model_id:
        additional_fields = {"thinking": {"type": "enabled", "budget_tokens": 10000}}

    # Execute the transformation
    with bedrock_client_context() as client:
        response = bedrock_converse(client, system_message, message, model_id, additional_model_request_fields=additional_fields)

    text = _extract_text(response)

    result = {}
    for field in ("steps", "nova_draft", "reflection", "nova_final"):
        value = parse_xml_tag(text, field, strict=True)
        if value is None:
            raise ValueError(f"Missing required field <{field}> in model response")
        result[field] = value

    return result


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
        model_id (str, optional): Model to use for classification.
            Defaults to DEFAULT_CLASSIFIER_MODEL_ID ('us.amazon.nova-2-lite-v1:0').

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

    if model_id is None:
        model_id = DEFAULT_CLASSIFIER_MODEL_ID

    # Load required prompt files
    system_prompt = load_text_file(os.path.join(DATA_DIR, "prompts"), "prompt_intent_classifier_system.txt")
    prompt_template = load_text_file(os.path.join(DATA_DIR, "prompts"), "prompt_intent_classifier.txt")

    # Format the prompt with XML output instructions
    formatted_prompt = prompt_template.format(input_prompt=prompt)
    formatted_prompt += OUTPUT_FORMAT_CLASSIFY.format(
        valid_intents=", ".join(VALID_INTENTS)
    )

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
        response = bedrock_converse(client, system_message, message, model_id, inference_config)

    text = _extract_text(response)
    reasoning = parse_xml_tag(text, "reasoning", strict=True) or ""
    raw_intents = parse_xml_tags(text, "intent")
    intents = [i for i in raw_intents if i in VALID_INTENTS]

    return {"reasoning": reasoning, "intents": intents}


# ============================================================================
# Combined pipeline
# ============================================================================

def transform_with_intent_classification(prompt, num_candidates=4, classifier_model_id=None,
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
        num_candidates (int): Number of candidate transformations to generate. Defaults to 4.
            Set to 1 to skip candidate generation and judging.
        classifier_model_id (str, optional): Model for intent classification.
            Defaults to DEFAULT_CLASSIFIER_MODEL_ID.
        transform_model_id (str, optional): Model for transformation.
            Defaults to DEFAULT_TRANSFORM_MODEL_ID.
        judge_model_id (str, optional): Model for judging candidates.
            Defaults to DEFAULT_JUDGE_MODEL_ID.
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
        ...     "Summarize this document", num_candidates=1
        ... )

        >>> # With API capability flags
        >>> result = transform_with_intent_classification(
        ...     "Analyze the chart and recommend next steps",
        ...     reasoning_mode=True,
        ...     image=True
        ... )
    """
    if max_workers is None:
        max_workers = num_candidates

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
    if num_candidates <= 1:
        transform_result = transform_prompt(prompt, **transform_kwargs)
        return {**metadata, **transform_result}

    # Step 4: Generate N candidates in parallel
    def _run_transform(_i):
        return transform_prompt(prompt, **transform_kwargs)

    candidates = [None] * num_candidates
    errors = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_transform, i): i for i in range(num_candidates)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                candidates[idx] = future.result()
            except Exception as e:
                errors.append(e)

    # Remove None entries (failed candidates)
    candidates = [c for c in candidates if c is not None]

    if len(candidates) == 0:
        raise RuntimeError(
            f"All {num_candidates} transformation attempts failed. Errors: {errors}"
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

def _escape_for_xml_wrapper(content, tag="candidate"):
    """Escape closing tags that would break the wrapper structure."""
    return content.replace(f"</{tag}>", f"&lt;/{tag}&gt;")


def _judge_candidates(original_prompt, candidates, model_id=None):
    """Judge multiple transformation candidates and select the best one.

    Args:
        original_prompt (str): The original prompt that was transformed.
        candidates (list): List of candidate result dicts, each containing 'nova_final'.
        model_id (str, optional): Model to use for judging.
            Defaults to DEFAULT_JUDGE_MODEL_ID ('us.anthropic.claude-sonnet-4-6').

    Returns:
        dict: Dictionary containing:
            - evaluations: List of per-candidate evaluation dicts
            - reasoning: Explanation of why the winner was selected
            - selected_candidate_id: 1-indexed ID of the winning candidate
    """
    if model_id is None:
        model_id = DEFAULT_JUDGE_MODEL_ID

    # Load judge prompt templates
    system_prompt = load_text_file(os.path.join(DATA_DIR, "prompts"), "prompt_judge_system.txt")
    prompt_template = load_text_file(os.path.join(DATA_DIR, "prompts"), "prompt_judge.txt")
    migration_guidelines = load_text_file(os.path.join(DATA_DIR, "docs", "nova"), "migration_guidelines.txt")

    # Format candidates as XML blocks
    candidate_blocks = []
    for i, candidate in enumerate(candidates, 1):
        escaped = _escape_for_xml_wrapper(candidate["nova_final"])
        candidate_blocks.append(f'<candidate id="{i}">\n{escaped}\n</candidate>')
    candidates_xml = "\n\n".join(candidate_blocks)

    # Format the judge prompt
    formatted_prompt = prompt_template.format(
        original_prompt=original_prompt,
        migration_guidelines=migration_guidelines,
        candidates_xml=candidates_xml,
        n=len(candidates),
    )

    # Binary metrics used for evaluation parsing
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

    # Build XML output format with metric tags
    metric_tags = "\n".join(f"<{m}>0 or 1</{m}>" for m in binary_metrics)
    formatted_prompt += OUTPUT_FORMAT_JUDGE.format(metric_tags=metric_tags)

    system_message = {"text": system_prompt}
    message = {
        "role": "user",
        "content": [{"text": formatted_prompt}],
    }

    additional_fields = {}
    if "amazon.nova-2" in model_id:
        additional_fields = {"inferenceConfig": {"reasoningConfig": {"type": "enabled", "maxReasoningEffort": "medium"}}}
        inference_config = {"maxTokens": 20000, "topP": 0.9, "temperature": 0.3}
    elif "anthropic.claude" in model_id:
        additional_fields = {"thinking": {"type": "enabled", "budget_tokens": 5000}}
        # Claude thinking requires temperature=1 and topP >= 0.95 or unset.
        inference_config = {"maxTokens": 20000, "temperature": 1}
    else:
        inference_config = {"maxTokens": 20000, "topP": 0.9, "temperature": 0.3}

    with bedrock_client_context() as client:
        response = bedrock_converse(client, system_message, message, model_id, inference_config, additional_model_request_fields=additional_fields)

    text = _extract_text(response)

    # Parse per-candidate evaluations
    evaluations = []
    for eval_block in parse_xml_tags(text, "evaluation"):
        eval_dict = {}
        cid = parse_xml_tag(eval_block, "candidate_id")
        eval_dict["candidate_id"] = int(cid) if cid else 0
        score_sum = 0
        for metric in binary_metrics:
            raw = parse_xml_tag(eval_block, metric)
            try:
                val = int(raw)
            except (TypeError, ValueError):
                val = 0
            eval_dict[metric] = val
            score_sum += val
        # Use model's total_score if present, otherwise recompute
        raw_total = parse_xml_tag(eval_block, "total_score")
        try:
            eval_dict["total_score"] = int(raw_total)
        except (TypeError, ValueError):
            eval_dict["total_score"] = score_sum
        evaluations.append(eval_dict)

    reasoning = parse_xml_tag(text, "reasoning", strict=True) or ""
    raw_selected = parse_xml_tag(text, "selected_candidate_id", strict=True)
    try:
        selected_candidate_id = int(raw_selected)
    except (TypeError, ValueError):
        # Fallback: pick candidate with highest total_score
        selected_candidate_id = max(evaluations, key=lambda e: e["total_score"])["candidate_id"] if evaluations else 1

    return {
        "evaluations": evaluations,
        "reasoning": reasoning,
        "selected_candidate_id": selected_candidate_id,
    }


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
        num_candidates=n,
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
