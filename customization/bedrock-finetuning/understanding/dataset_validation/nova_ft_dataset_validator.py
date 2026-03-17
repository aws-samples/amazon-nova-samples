#!/usr/bin/env python3
"""
Nova Dataset Validator

Standalone CLI tool that validates JSONL training/validation datasets for
Amazon Nova fine-tuning. Combines the Pydantic-based schema validation from
nova_ft_dataset_validator.py with the skip-bad-samples mode, validation-file
support, structured reporting, and CPT/document checks from validate_dataset.py.

Supported recipe types:
  - SFT   Nova 1.0 & 2.0 Supervised Fine-Tuning (Converse format)
  - CPT   Continued Pre-Training (plain "text" field)
  - DPO   Direct Preference Optimization (Converse with candidates)
  - RFT   Reinforcement Fine-Tuning (OpenAI-style with tools, lite-2.0 only)

Usage examples:
  python nova_dataset_validator.py -i train.jsonl -m lite -t sft

  python nova_dataset_validator.py -i train.jsonl --validation val.jsonl \\
      -m lite-2.0 -t sft --skip-bad-samples

  python nova_dataset_validator.py -i train.jsonl -m lite-2.0 -t rft
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional, Tuple, Union, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

# ===========================================================================
# Constants
# ===========================================================================

IMAGE_FORMATS = ["jpeg", "png", "gif", "webp"]
VIDEO_FORMATS = ["mov", "mkv", "mp4", "webm"]
DOCUMENT_FORMATS = ["pdf"]

# Nova 2.0 Lite restricted formats
NOVA_2_0_LITE_IMAGE_FORMATS = ["png", "jpeg", "gif"]
NOVA_2_0_LITE_VIDEO_FORMATS = ["mov", "mkv", "mp4"]
NOVA_2_0_LITE_DOCUMENT_FORMATS = ["pdf"]

MAX_NUM_IMAGES = 10
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024     # 10 MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024     # 50 MB

MODEL_TO_NUM_SAMPLES_MAP: Dict[str, Tuple[int, int]] = {
    "micro": (8, 20000),
    "micro-1.0": (8, 20000),
    "lite": (8, 20000),
    "lite-1.0": (8, 20000),
    "lite-2.0": (8, 20000),
    "pro": (8, 20000),
    "pro-1.0": (8, 20000),
}

# Nova 2.0 Lite task-specific sample bounds
NOVA_2_0_LITE_SAMPLE_BOUNDS: Dict[str, Tuple[int, int]] = {
    "SFT": (200, 20000),
    "RFT": (100, 20000),
}

REASONING_SUPPORTED_MODELS = ["lite-2.0"]

INVALID_TOKENS_TEXT = [
    "System:", "SYSTEM:",
    "User:", "user:" "USER:",
    "Bot:", "BOT:", "bot:"
    "Assistant:", "ASSISTANT:", "assistant:"
    "Thought:", "thought:" "THOUGHT:"
    "[EOS]", "<image>", "<video>", "<unk>",
]


# ===========================================================================
# Enums & lightweight types
# ===========================================================================


class PreferenceLabels:
    PREFERRED = "preferred"
    NON_PREFERRED = "non-preferred"


PREFERENCE_LABELS = [PreferenceLabels.PREFERRED, PreferenceLabels.NON_PREFERRED]


class TaskType(Enum):
    SFT = "SFT"
    CPT = "CPT"
    DPO = "DPO"
    RFT = "RFT"


class ConverseRoles:
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


CONVERSE_ROLES_WITHOUT_SYSTEM = [ConverseRoles.USER, ConverseRoles.ASSISTANT]


class ErrorCategory(str, Enum):
    JSON_PARSE = "json_parse_error"
    SCHEMA = "schema_error"
    ROLE_ORDER = "role_ordering_error"
    EMPTY_CONTENT = "empty_content_error"
    INVALID_TOKEN = "invalid_token_error"
    IMAGE = "image_error"
    VIDEO = "video_error"
    DOCUMENT = "document_error"
    TOOL_USE = "tool_use_error"
    PREFERENCE = "preference_error"
    SAMPLE_BOUNDS = "sample_bounds_error"
    FILE_FORMAT = "file_format_error"
    MISSING_FIELD = "missing_field_error"
    CONTENT_RULE = "content_rule_error"


# ===========================================================================
# Exceptions
# ===========================================================================


class NovaClientError(ValueError):
    """Validation error caused by customer input."""

    def __init__(self, message):
        super().__init__(message)


class NovaInternalError(Exception):
    """Internal / unexpected error during validation."""

    pass


# ===========================================================================
# Reporting (from validate_dataset.py)
# ===========================================================================


@dataclass
class ValidationErrorItem:
    """A single validation error for a sample."""
    line: int
    category: ErrorCategory
    message: str


@dataclass
class ValidationReport:
    """Aggregated validation report for one file."""
    file_path: str
    total_samples: int = 0
    valid_samples: int = 0
    failed_samples: int = 0
    errors: List[ValidationErrorItem] = field(default_factory=list)
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def pass_rate(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return (self.valid_samples / self.total_samples) * 100

    def add_error(self, line: int, category: ErrorCategory, message: str):
        self.error_counts[category.value] += 1
        self.errors.append(ValidationErrorItem(line=line, category=category, message=message))

    def summary(self) -> str:
        lines = [
            f"\n{'='*60}",
            f"  Dataset Validation Report: {self.file_path}",
            f"{'='*60}",
            f"  Total samples:   {self.total_samples}",
            f"  Valid samples:   {self.valid_samples}",
            f"  Failed samples:  {self.failed_samples}",
            f"  Pass rate:       {self.pass_rate:.1f}%",
        ]
        if self.error_counts:
            lines.append("\n  Error breakdown:")
            for cat, count in sorted(self.error_counts.items(), key=lambda x: -x[1]):
                lines.append(f"    {cat}: {count}")
        if self.errors:
            lines.append("\n  First errors (up to 20):")
            for err in self.errors[:20]:
                lines.append(f"    Line {err.line}: [{err.category.value}] {err.message}")
        lines.append(f"{'='*60}\n")
        return "\n".join(lines)


# ===========================================================================
# Low-level helpers
# ===========================================================================


def check_jsonl_file(file_path: str):
    """Validates that the input file has a .jsonl extension."""
    if not file_path.endswith(".jsonl"):
        raise NovaClientError(f"File is not jsonl: {file_path}")


def load_jsonl_data(file_path: str) -> List[dict]:
    """Loads and validates JSON lines from the specified file path."""
    try:
        check_jsonl_file(file_path)
        data: List[dict] = []
        with open(file_path, "r") as f:
            for line_number, line in enumerate(f, 1):
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Line {line_number}: Invalid JSON syntax - {str(e)}\nLine content: {line}"
                    )
                data.append(parsed)
        return data
    except NovaClientError:
        raise
    except Exception as e:
        raise NovaClientError(f"Error loading data from {file_path}: {str(e)}")


def is_valid_path(file_path: str):
    """Validates that file path contains only safe characters."""
    pattern = r"^[\w\-/\.]+$"
    if not re.match(pattern, file_path):
        raise ValueError(
            "Invalid characters in 'uri'. Only alphanumeric, underscores, hyphens, slashes, and dots are allowed"
        )


def validate_invalid_tokens(text: str):
    """Validates that the input text does not contain any disallowed tokens (case-insensitive)."""
    stripped_text = text.strip()
    lower_text = stripped_text.lower()
    client_invalid_tokens = []
    for invalid_token in INVALID_TOKENS_TEXT:
        if invalid_token.lower() in lower_text:
            client_invalid_tokens.append(f"`{invalid_token}`")
    if client_invalid_tokens:
        client_invalid_tokens_str = ", ".join(client_invalid_tokens)
        raise ValueError(
            f"Invalid text content, following tokens are invalid: {client_invalid_tokens_str}. "
            f"Please check documentation for other invalid tokens"
        )


def check_roles_order(messages):
    """Validates that messages alternate between user and assistant roles."""
    if len(messages) < 2:
        raise ValueError(
            f"Invalid messages, both {CONVERSE_ROLES_WITHOUT_SYSTEM} are needed in sample"
        )
    for i, message in enumerate(messages):
        if i % 2 == 0 and message.role != ConverseRoles.USER:
            raise ValueError(
                f"Invalid messages, expected {ConverseRoles.USER} role but found {message.role}"
            )
        elif i % 2 == 1 and message.role != ConverseRoles.ASSISTANT:
            raise ValueError(
                f"Invalid messages, expected {ConverseRoles.ASSISTANT} role but found {message.role}"
            )
    if messages[-1].role != ConverseRoles.ASSISTANT:
        raise ValueError(
            f"Invalid messages, last turn should have {ConverseRoles.ASSISTANT} role"
        )


def validate_role_name(role: str):
    """Validates that the role is either user or assistant."""
    if role.lower() not in CONVERSE_ROLES_WITHOUT_SYSTEM:
        raise ValueError(
            f"Invalid value for role, valid values are {CONVERSE_ROLES_WITHOUT_SYSTEM}"
        )


def validate_one_document_per_sample(messages):
    """At most one document across all messages in a sample."""
    doc_count = 0
    for message in messages:
        for item in message.content:
            if item.document is not None:
                doc_count += 1
    if doc_count > 1:
        raise ValueError("Only one document is allowed per sample")


def get_data_record_bounds(model_name: str, task_type: str) -> Tuple[int, int]:
    """Returns (min, max) sample bounds for a given model and task type."""
    if model_name == "lite-2.0" and task_type.upper() in NOVA_2_0_LITE_SAMPLE_BOUNDS:
        return NOVA_2_0_LITE_SAMPLE_BOUNDS[task_type.upper()]
    return MODEL_TO_NUM_SAMPLES_MAP.get(model_name, (8, 20000))


def validate_data_record_bounds(num_samples: int, model_name: str, task_type: str):
    """Validates that the number of samples is within allowed bounds."""
    lo, hi = get_data_record_bounds(model_name, task_type)
    if num_samples < lo or num_samples > hi:
        raise NovaClientError(
            f"Number of samples {num_samples} out of bounds between {lo} and {hi} "
            f"for {model_name} with task type {task_type}"
        )


# ===========================================================================
# Pydantic models — Converse format (SFT / DPO)
# ===========================================================================


class S3Location(BaseModel):
    """Represents and validates an S3 URI location."""
    uri: str
    bucketOwner: Optional[str] = None

    @field_validator("uri")
    def validate_format(cls, uri):
        if not uri.startswith("s3://"):
            raise ValueError("Invalid S3 URI, must start with 's3://'")
        is_valid_path(uri.replace("s3://", ""))
        return uri


class Source(BaseModel):
    s3Location: S3Location


class ImageContent(BaseModel):
    format: str
    source: Source

    @field_validator("format")
    def validate_format(cls, image_format):
        if image_format.lower() not in IMAGE_FORMATS:
            raise ValueError(f"Invalid image format, supported formats are {IMAGE_FORMATS}")
        return image_format


class VideoContent(BaseModel):
    format: str
    source: Source

    @field_validator("format")
    def validate_format(cls, video_format):
        if video_format.lower() not in VIDEO_FORMATS:
            raise ValueError(f"Invalid video format, supported formats are {VIDEO_FORMATS}")
        return video_format


class DocumentContent(BaseModel):
    format: str
    source: Source

    @field_validator("format")
    def validate_format(cls, document_format):
        if document_format.lower() not in DOCUMENT_FORMATS:
            raise ValueError(f"Invalid document format, supported formats are {DOCUMENT_FORMATS}")
        return document_format


class ReasoningText(BaseModel):
    text: str

    @field_validator("text")
    def validate_text(cls, text: str):
        if not text:
            raise ValueError("Invalid reasoningText, text field cannot be empty")
        validate_invalid_tokens(text)
        return text


class ReasoningContent(BaseModel):
    reasoningText: ReasoningText

    @field_validator("reasoningText")
    def validate_reasoning_text(cls, reasoning_text):
        if reasoning_text is None:
            raise ValueError("Invalid reasoningContent, reasoningText field is required")
        return reasoning_text


# --- Tool models (Converse toolConfig) ---

class InputSchema(BaseModel):
    json: dict

    @field_validator("json")
    def validate_json_schema(cls, schema):
        if not isinstance(schema, dict):
            raise ValueError("Invalid inputSchema, json field must be a valid JSON Schema object")
        if "type" not in schema:
            raise ValueError("Invalid inputSchema, json must have a 'type' field")
        return schema


class ToolSpec(BaseModel):
    name: str
    description: str
    inputSchema: InputSchema

    @field_validator("name")
    def validate_name(cls, name):
        if not name or not name.strip():
            raise ValueError("Invalid toolSpec, name cannot be empty")
        return name

    @field_validator("description")
    def validate_description(cls, description):
        if not description or not description.strip():
            raise ValueError("Invalid toolSpec, description cannot be empty")
        return description


class Tool(BaseModel):
    toolSpec: ToolSpec


class ToolConfig(BaseModel):
    tools: List[Tool]

    @field_validator("tools")
    def validate_tools(cls, tools):
        if not tools:
            raise ValueError("Invalid toolConfig, tools list cannot be empty")
        tool_names = [t.toolSpec.name for t in tools]
        if len(tool_names) != len(set(tool_names)):
            raise ValueError("Invalid toolConfig, duplicate tool names found")
        return tools


class ToolUse(BaseModel):
    toolUseId: str
    name: str
    input: dict

    @field_validator("toolUseId")
    def validate_tool_use_id(cls, tool_use_id):
        if not tool_use_id or not tool_use_id.strip():
            raise ValueError("Invalid toolUse, toolUseId cannot be empty")
        return tool_use_id

    @field_validator("name")
    def validate_name(cls, name):
        if not name or not name.strip():
            raise ValueError("Invalid toolUse, name cannot be empty")
        return name

    @field_validator("input")
    def validate_input(cls, input_data):
        if not isinstance(input_data, dict):
            raise ValueError("Invalid toolUse, input must be a JSON object")
        return input_data


class ToolResultContentItem(BaseModel):
    text: Optional[str] = None
    json: Optional[dict] = None

    @model_validator(mode="after")
    def validate_content(cls, values):
        if values.text is None and values.json is None:
            raise ValueError("Invalid toolResult content, either text or json must be provided")
        if values.text is not None and values.json is not None:
            raise ValueError("Invalid toolResult content, cannot have both text and json")
        return values


class ToolResult(BaseModel):
    toolUseId: str
    content: List[ToolResultContentItem]

    @field_validator("toolUseId")
    def validate_tool_use_id(cls, tool_use_id):
        if not tool_use_id or not tool_use_id.strip():
            raise ValueError("Invalid toolResult, toolUseId cannot be empty")
        return tool_use_id

    @field_validator("content")
    def validate_content(cls, content):
        if not content:
            raise ValueError("Invalid toolResult, content list cannot be empty")
        return content


# --- ContentItem ---

class ContentItem(BaseModel):
    """A single content block inside a message."""
    text: Optional[str] = None
    image: Optional[ImageContent] = None
    video: Optional[VideoContent] = None
    document: Optional[DocumentContent] = None
    reasoningContent: Optional[ReasoningContent] = None
    toolUse: Optional[ToolUse] = None
    toolResult: Optional[ToolResult] = None

    @model_validator(mode="after")
    def validate_model_fields(cls, values):
        if not any(getattr(values, f) is not None for f in cls.model_fields.keys()):
            raise ValueError(
                f"Invalid content, at least one of {list(cls.model_fields.keys())} must be provided"
            )
        if values.reasoningContent is not None:
            if values.image is not None or values.video is not None:
                raise ValueError(
                    "Invalid content, reasoningContent cannot be used with image or video content"
                )
        if values.toolUse is not None and values.toolResult is not None:
            raise ValueError(
                "Invalid content, toolUse and toolResult cannot coexist in the same ContentItem"
            )
        return values

    @field_validator("text")
    def validate_text(cls, text: str):
        if not text:
            return text
        validate_invalid_tokens(text)
        return text


# --- Candidate (DPO) ---

class CandidateItem(BaseModel):
    content: List[ContentItem]
    preferenceLabel: str

    @field_validator("content")
    def validate_content(cls, content):
        has_video = any(item.video is not None for item in content)
        has_image = any(item.image is not None for item in content)
        has_document = any(item.document is not None for item in content)
        has_reasoning = any(item.reasoningContent is not None for item in content)

        if has_video or has_image or has_document:
            raise ValueError(
                "Invalid content, candidate contents cannot include image/video/document"
            )
        total_text_length = sum(len(item.text) for item in content if item.text is not None)
        if total_text_length == 0 and not has_reasoning:
            raise ValueError("Invalid content, empty text content")
        return content

    @field_validator("preferenceLabel")
    def validate_preference_label(cls, preference_label):
        if preference_label.lower() not in PREFERENCE_LABELS:
            raise ValueError(
                f"Invalid value for preferenceLabel, valid values are {PREFERENCE_LABELS}"
            )
        return preference_label


class CandidatesMessage(BaseModel):
    role: str
    candidates: List[CandidateItem]

    @field_validator("role")
    def validate_role(cls, role):
        validate_role_name(role)
        return role

    @field_validator("candidates")
    def validate_candidates(cls, candidates):
        if len(candidates) < 2:
            raise ValueError("Invalid candidates, candidates list must have at least two items")
        preference_labels = set(c.preferenceLabel for c in candidates)
        if len(preference_labels) < 2:
            raise ValueError(
                "Invalid candidates, all candidates cannot have the same preferenceLabel"
            )
        return candidates


# --- Message ---

class Message(BaseModel):
    """A conversation message with role and content."""
    role: str
    content: List[ContentItem]

    @field_validator("role")
    def validate_role(cls, role):
        validate_role_name(role)
        return role

    @model_validator(mode="after")
    def validate_content_rules(cls, values):
        content_items = values.content
        has_video = any(item.video is not None for item in content_items)
        has_image = any(item.image is not None for item in content_items)
        has_document = any(item.document is not None for item in content_items)
        has_reasoning = any(item.reasoningContent is not None for item in content_items)
        has_tool_result = any(item.toolResult is not None for item in content_items)
        has_tool_use = any(item.toolUse is not None for item in content_items)

        if (has_image or has_video or has_document or has_tool_result) and values.role.lower() == ConverseRoles.ASSISTANT:
            raise ValueError(
                "Invalid content, image/video/document/toolResult cannot be included when role is 'assistant'"
            )
        if has_tool_use and values.role.lower() == ConverseRoles.USER:
            raise ValueError("Invalid content, toolUse cannot be included when role is 'user'")
        if has_reasoning and values.role.lower() != ConverseRoles.ASSISTANT:
            raise ValueError(
                "Invalid content, reasoningContent can only be included in assistant messages"
            )
        return values

    @field_validator("content")
    def validate_content(cls, content, info: ValidationInfo):
        has_text = any(item.text is not None for item in content)
        has_video = any(item.video is not None for item in content)
        has_image = any(item.image is not None for item in content)
        has_document = any(item.document is not None for item in content)
        has_tool_use = any(item.toolUse is not None for item in content)
        has_tool_result = any(item.toolResult is not None for item in content)
        has_reasoning = any(item.reasoningContent is not None for item in content)

        if not (has_text or has_image or has_video or has_document or has_tool_use or has_tool_result):
            raise ValueError(
                "'content' list must have at least one 'text', 'image', 'video', 'document', 'toolUse', or 'toolResult'"
            )

        total_text_length = sum(len(item.text) for item in content if item.text is not None)
        if has_text and not (has_image or has_video or has_document or has_reasoning) and total_text_length == 0:
            raise ValueError("Invalid content, empty text content")

        if not info.context:
            raise NovaInternalError("context is not set for validating model type")

        model_name = info.context["model_name"]
        is_micro_model = "micro" in model_name
        if is_micro_model and (has_image or has_video or has_document):
            raise ValueError(
                "Invalid content, image/video/document samples not supported by Nova Micro model"
            )

        if has_reasoning and model_name not in REASONING_SUPPORTED_MODELS:
            raise ValueError(
                f"Invalid content, reasoning samples are only supported by Nova 2.0 Lite. "
                f"Model '{model_name}' does not support reasoning. Use 'lite-2.0' for reasoning support."
            )

        # Nova 2.0 Lite format restrictions
        if model_name == "lite-2.0":
            for item in content:
                if item.image is not None and item.image.format.lower() not in NOVA_2_0_LITE_IMAGE_FORMATS:
                    raise ValueError(
                        f"Invalid image format '{item.image.format}' for lite-2.0. "
                        f"Supported formats: {', '.join(NOVA_2_0_LITE_IMAGE_FORMATS)}"
                    )
            for item in content:
                if item.video is not None and item.video.format.lower() not in NOVA_2_0_LITE_VIDEO_FORMATS:
                    raise ValueError(
                        f"Invalid video format '{item.video.format}' for lite-2.0. "
                        f"Supported formats: {', '.join(NOVA_2_0_LITE_VIDEO_FORMATS)}"
                    )

        if sum(1 for item in content if item.video is not None) > 1:
            raise ValueError("Only one video is allowed per sample")

        if has_video and (has_image or has_document):
            raise ValueError(
                "'content' list cannot contain both video items and image/document items for a given sample"
            )

        num_docs = sum(1 for item in content if item.document is not None)
        if num_docs > 1:
            raise ValueError("Only one document is allowed per user turn")

        num_images = sum(1 for item in content if item.image is not None)
        if num_images > MAX_NUM_IMAGES:
            raise ValueError(
                f"Invalid content, number of images {num_images} exceed maximum allowed limit of {MAX_NUM_IMAGES}"
            )

        return content


class SystemMessage(BaseModel):
    text: str

    @field_validator("text")
    def validate_text(cls, text: str):
        if not text:
            return text
        validate_invalid_tokens(text)
        return text


# --- Top-level sample models ---

class ConverseDatasetSample(BaseModel):
    """SFT sample in Converse format."""
    schemaVersion: Optional[str] = None
    system: Optional[List[SystemMessage]] = None
    toolConfig: Optional[ToolConfig] = None
    messages: List[Message]

    @field_validator("messages")
    def validate_data_sample_rules(cls, messages):
        validate_one_document_per_sample(messages)
        check_roles_order(messages)
        return messages

    @model_validator(mode="after")
    def validate_tool_use_rules(cls, values):
        if values.toolConfig is not None:
            validate_tool_use_in_conversation(values.messages, values.toolConfig)
        return values


MessageOrCandidate = Annotated[
    Union[
        Annotated[Message, Tag("Message")],
        Annotated[CandidatesMessage, Tag("CandidatesMessage")],
    ],
    Discriminator(lambda message: "CandidatesMessage" if "candidates" in message else "Message"),
]


class ConverseDatasetSampleWithCandidates(BaseModel):
    """DPO sample in Converse format with candidates."""
    schemaVersion: Optional[str] = None
    system: Optional[List[SystemMessage]] = None
    messages: List[MessageOrCandidate]

    @field_validator("messages")
    def validate_data_sample_rules(cls, messages: List[MessageOrCandidate]):
        if any(isinstance(message, CandidatesMessage) for message in messages[:-1]):
            raise ValueError("Invalid messages, only the last message can be a candidates message")
        if not isinstance(messages[-1], CandidatesMessage):
            raise ValueError("Invalid messages, last message must be a candidates message")
        if any(
            item.video for message in cast(List[Message], messages[:-1]) for item in message.content
        ):
            raise ValueError("Invalid sample, video content is not supported for DPO")
        validate_one_document_per_sample(cast(List[Message], messages[:-1]))
        check_roles_order(messages)
        return messages


def validate_tool_use_in_conversation(messages: List[Message], tool_config: ToolConfig):
    """Validates that tool use in the conversation follows proper rules."""
    available_tools = {tool.toolSpec.name for tool in tool_config.tools}
    tool_use_ids: Dict[str, str] = {}
    tool_result_ids: set = set()

    for message in messages:
        for content_item in message.content:
            if content_item.toolUse is not None:
                tool_use = content_item.toolUse
                if tool_use.name not in available_tools:
                    raise ValueError(
                        f"Invalid toolUse, tool '{tool_use.name}' not found in toolConfig"
                    )
                if tool_use.toolUseId in tool_use_ids:
                    raise ValueError(
                        f"Invalid toolUse, duplicate toolUseId '{tool_use.toolUseId}'"
                    )
                tool_use_ids[tool_use.toolUseId] = tool_use.name

            if content_item.toolResult is not None:
                tool_result = content_item.toolResult
                if tool_result.toolUseId not in tool_use_ids:
                    raise ValueError(
                        f"Invalid toolResult, toolUseId '{tool_result.toolUseId}' not found in previous toolUse"
                    )
                if tool_result.toolUseId in tool_result_ids:
                    raise ValueError(
                        f"Invalid toolResult, duplicate toolUseId '{tool_result.toolUseId}'"
                    )
                tool_result_ids.add(tool_result.toolUseId)


# ===========================================================================
# Pydantic models — RFT format (lite-2.0 only)
# ===========================================================================


class RFTFunctionParameters(BaseModel):
    type: str
    properties: dict
    required: Optional[List[str]] = None

    @field_validator("type")
    def validate_type(cls, param_type):
        if param_type != "object":
            raise ValueError("Invalid parameters type, must be 'object'")
        return param_type

    @field_validator("properties")
    def validate_properties(cls, properties):
        if not isinstance(properties, dict):
            raise ValueError("Invalid properties, must be a dictionary")
        return properties


class RFTFunction(BaseModel):
    name: str
    description: str
    parameters: RFTFunctionParameters

    @field_validator("name")
    def validate_name(cls, name):
        if not name or not name.strip():
            raise ValueError("Invalid function name, cannot be empty")
        return name

    @field_validator("description")
    def validate_description(cls, description):
        if not description or not description.strip():
            raise ValueError("Invalid function description, cannot be empty")
        return description


class RFTTool(BaseModel):
    type: str
    function: RFTFunction

    @field_validator("type")
    def validate_type(cls, tool_type):
        if tool_type != "function":
            raise ValueError("Invalid tool type, must be 'function'")
        return tool_type


class RFTMessage(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None

    @field_validator("role")
    def validate_role(cls, role):
        if role is not None:
            valid_roles = ["system", "user", "assistant"]
            if role.lower() not in valid_roles:
                raise ValueError(f"Invalid role, must be one of {valid_roles}")
        return role

    @field_validator("content")
    def validate_content(cls, content):
        if content is not None:
            if not content.strip():
                raise ValueError("Invalid content, if provided cannot be empty")
            validate_invalid_tokens(content)
        return content


class RFTDatasetSample(BaseModel):
    """RFT sample with messages and optional tools."""
    id: Optional[str] = None
    messages: List[RFTMessage]
    tools: Optional[List[RFTTool]] = None
    reference_answer: Optional[Union[str, dict]] = None

    @field_validator("id")
    def validate_id(cls, sample_id):
        if sample_id is not None and (not sample_id or not sample_id.strip()):
            raise ValueError("Invalid id, if provided cannot be empty")
        return sample_id

    @field_validator("messages")
    def validate_messages(cls, messages):
        if not messages:
            raise ValueError("Invalid messages, cannot be empty")
        has_system = any(msg.role and msg.role.lower() == "system" for msg in messages)
        if has_system:
            first_role = messages[0].role.lower() if messages[0].role else None
            if first_role != "system":
                raise ValueError("Invalid messages, system message must be first if present")
        if not any(msg.role and msg.role.lower() == "user" for msg in messages):
            raise ValueError("Invalid messages, must have at least one user message")
        return messages

    @field_validator("reference_answer")
    def validate_reference_answer(cls, reference_answer):
        if reference_answer is not None:
            if isinstance(reference_answer, str):
                if not reference_answer.strip():
                    raise ValueError("Invalid reference_answer, if provided as string cannot be empty")
            elif isinstance(reference_answer, dict):
                if not reference_answer:
                    raise ValueError("Invalid reference_answer, if provided as dict cannot be empty")
            else:
                raise ValueError("Invalid reference_answer, must be a string or dictionary")
        return reference_answer

    @field_validator("tools")
    def validate_tools(cls, tools):
        if tools is not None:
            if len(tools) == 0:
                raise ValueError("Invalid tools, if provided cannot be an empty list")
            tool_names = [tool.function.name for tool in tools]
            if len(tool_names) != len(set(tool_names)):
                raise ValueError("Invalid tools, duplicate tool names found")
        return tools


# ===========================================================================
# Pydantic model — CPT format (from validate_dataset.py)
# ===========================================================================


class CPTDatasetSample(BaseModel):
    """CPT (Continued Pre-Training) sample — plain text."""
    text: str

    @field_validator("text")
    def validate_text(cls, text: str):
        if not isinstance(text, str):
            raise ValueError("'text' field must be a string")
        if len(text.strip()) == 0:
            raise ValueError("'text' field must not be empty")
        return text


# ===========================================================================
# Core validation orchestration
# ===========================================================================


def _get_pydantic_model_for_task(task_type: TaskType):
    """Return the Pydantic model class for the given task type."""
    if task_type is TaskType.SFT:
        return ConverseDatasetSample
    elif task_type is TaskType.DPO:
        return ConverseDatasetSampleWithCandidates
    elif task_type is TaskType.RFT:
        return RFTDatasetSample
    elif task_type is TaskType.CPT:
        return CPTDatasetSample
    raise NovaClientError(f"Unsupported task type: {task_type}")


def _needs_model_context(task_type: TaskType) -> bool:
    """Whether the Pydantic model needs a validation context with model_name."""
    return task_type in (TaskType.SFT, TaskType.DPO)


def _categorize_error(msg: str) -> ErrorCategory:
    """Best-effort categorization of an error message."""
    lower = msg.lower()
    if "role" in lower and ("order" in lower or "expected" in lower or "alternating" in lower):
        return ErrorCategory.ROLE_ORDER
    if "invalid value for role" in lower or "invalid role" in lower:
        return ErrorCategory.ROLE_ORDER
    if "empty text" in lower or "empty content" in lower:
        return ErrorCategory.EMPTY_CONTENT
    if "invalid" in lower and "token" in lower:
        return ErrorCategory.INVALID_TOKEN
    if "image" in lower and ("format" in lower or "dimension" in lower or "not supported" in lower):
        return ErrorCategory.IMAGE
    if "video" in lower:
        return ErrorCategory.VIDEO
    if "document" in lower:
        return ErrorCategory.DOCUMENT
    if "tooluse" in lower or "toolresult" in lower or "tool_use" in lower:
        return ErrorCategory.TOOL_USE
    if "preference" in lower or "candidate" in lower:
        return ErrorCategory.PREFERENCE
    if "missing" in lower or "field required" in lower:
        return ErrorCategory.MISSING_FIELD
    return ErrorCategory.SCHEMA


# ===========================================================================
# File-level validation with skip-bad-samples support
# ===========================================================================


def validate_jsonl_file(
    file_path: str,
    model_name: str,
    task_type: TaskType,
    platform: str = "bedrock",
    skip_bad_samples: bool = False,
) -> ValidationReport:
    """
    Validate a single JSONL file line-by-line using Pydantic models.

    Args:
        file_path: Path to the .jsonl file.
        model_name: Short model name (micro, lite, lite-2.0, pro, etc.).
        task_type: TaskType enum.
        platform: "bedrock" or "sagemaker".
        skip_bad_samples: If True, continue past bad samples to report all issues.

    Returns:
        ValidationReport with all findings.
    """
    report = ValidationReport(file_path=file_path)

    # File extension check
    if not file_path.endswith(".jsonl"):
        report.add_error(0, ErrorCategory.FILE_FORMAT, f"File '{file_path}' is not a .jsonl file")
        return report

    # Task / model compatibility checks
    if task_type is TaskType.RFT and model_name != "lite-2.0":
        report.add_error(
            0, ErrorCategory.SCHEMA,
            f"RFT task type is only supported on lite-2.0 model. Current model: {model_name}."
        )
        return report

    if task_type is TaskType.DPO and model_name == "lite-2.0":
        report.add_error(
            0, ErrorCategory.SCHEMA,
            "DPO task type is not supported on Nova 2.0 (lite-2.0). Use SFT or RFT instead."
        )
        return report

    pydantic_model = _get_pydantic_model_for_task(task_type)
    use_context = _needs_model_context(task_type)
    context = {"model_name": model_name} if use_context else None

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            report.total_samples += 1

            # JSON parse
            try:
                sample = json.loads(raw_line)
            except json.JSONDecodeError as e:
                report.failed_samples += 1
                report.add_error(
                    line_num, ErrorCategory.JSON_PARSE,
                    f"Line {line_num}: Invalid JSON syntax - {e}",
                )
                if not skip_bad_samples:
                    break
                continue

            # Pydantic validation
            try:
                if context:
                    pydantic_model.model_validate(sample, context=context)
                else:
                    pydantic_model.model_validate(sample)
                report.valid_samples += 1
            except ValidationError as e:
                report.failed_samples += 1
                for err in e.errors():
                    err_msg = err["msg"].replace("Value error, ", "")
                    loc = err["loc"]
                    full_msg = f"Location {loc}: {err_msg} (type={err['type']})"
                    cat = _categorize_error(err_msg)
                    report.add_error(line_num, cat, full_msg)
                if not skip_bad_samples:
                    break
            except NovaInternalError as e:
                report.failed_samples += 1
                report.add_error(line_num, ErrorCategory.SCHEMA, f"Internal error: {e}")
                if not skip_bad_samples:
                    break

    if skip_bad_samples:
        report.valid_samples = report.total_samples - report.failed_samples

    return report


# ===========================================================================
# Dataset-level constraint checks
# ===========================================================================


def validate_dataset_level(
    train_report: ValidationReport,
    val_report: Optional[ValidationReport],
    model_name: str,
    task_type: str,
) -> List[str]:
    """
    Check dataset-level constraints: sample count bounds, Nova 2.0 validation-set
    restriction, combined train+val limits.

    Returns list of dataset-level error strings.
    """
    dataset_errors: List[str] = []

    if model_name == "lite-2.0" and val_report is not None:
        dataset_errors.append("Nova 2.0 (lite-2.0) does not support a validation dataset")

    train_count = train_report.valid_samples if train_report else 0
    total_count = train_count
    if val_report:
        total_count += val_report.valid_samples

    lo, hi = get_data_record_bounds(model_name, task_type)

    if train_count < lo:
        dataset_errors.append(
            f"Number of valid training samples ({train_count}) is below the minimum of {lo} "
            f"for {model_name} with task type {task_type}"
        )
    if total_count > hi:
        dataset_errors.append(
            f"Total number of samples ({total_count}) exceeds the maximum of {hi} "
            f"for {model_name} with task type {task_type}"
        )

    return dataset_errors


# ===========================================================================
# Legacy entry point (backwards-compatible with nova_ft_dataset_validator.py)
# ===========================================================================


def validate_converse_dataset(args):
    """
    Validates the entire conversation dataset against Nova format requirements.
    Kept for backwards compatibility with the original nova_ft_dataset_validator.py CLI.
    """
    try:
        samples = load_jsonl_data(args.input_file)
        num_samples = len(samples)
        print(f"Loaded {num_samples} samples from {args.input_file}")

        platform = getattr(args, "platform", "bedrock")
        if platform.lower() == "bedrock":
            print(f"Platform: {platform} - Validating data record bounds")
            validate_data_record_bounds(num_samples, args.model_name, args.task_type)
        else:
            print(f"Platform: {platform} - Skipping data record bounds validation")
    except Exception as e:
        print(f"Error loading or validating file bounds: {e}")
        raise

    error_message = ""
    failed_samples_id_list: List[int] = []

    task_type = TaskType(str(args.task_type).upper())
    print(f"Validating samples for model: {args.model_name}, task: {task_type.value}")

    if task_type is TaskType.RFT and args.model_name != "lite-2.0":
        raise NovaClientError(
            f"RFT task type is only supported on lite-2.0 model. "
            f"Current model: {args.model_name}. Please use -m lite-2.0 for RFT tasks."
        )
    if task_type is TaskType.DPO and args.model_name == "lite-2.0":
        raise NovaClientError(
            f"DPO task type is not supported on Nova 2.0 (lite-2.0) model. "
            f"DPO is only available for Nova 1.0 models. "
            f"For Nova 2.0, please use SFT or RFT task types."
        )

    for i, sample in enumerate(samples):
        try:
            if task_type is TaskType.RFT:
                RFTDatasetSample.model_validate(sample)
            elif task_type is TaskType.CPT:
                CPTDatasetSample.model_validate(sample)
            elif task_type is TaskType.DPO:
                ConverseDatasetSampleWithCandidates.model_validate(
                    sample, context={"model_name": args.model_name}
                )
            else:
                ConverseDatasetSample.model_validate(
                    sample, context={"model_name": args.model_name}
                )
        except ValidationError as e:
            failed_samples_id_list.append(i)
            error_message += f"\nSample {i}:\n"
            for err in e.errors():
                err["msg"] = err["msg"].replace("Value error, ", "")
                error_message += f"  - Location {err['loc']}: {err['msg']} (type={err['type']})\n"
        except Exception as e:
            raise NovaInternalError(f"Unexpected error occurred in sample {i}: {e}")

    if error_message:
        if len(failed_samples_id_list) > 3:
            ids = failed_samples_id_list
            failed_samples_str = f"[{ids[0]}, {ids[1]}, ...{ids[-1]}]"
        else:
            failed_samples_str = f"{failed_samples_id_list}"
        final_err_msg = (
            f"Validation failed for samples: {failed_samples_str}\n\n"
            f"Note: Sample IDs are zero-indexed.\n"
            f"{error_message}"
        )
        raise NovaClientError(final_err_msg)
    else:
        print("Validation successful, all samples passed!")


# ===========================================================================
# CLI entry point
# ===========================================================================


def build_parser() -> argparse.ArgumentParser:
    description = """
Nova Dataset Validator — validates JSONL datasets for Amazon Nova fine-tuning.
Supports SFT, CPT, DPO, and RFT recipe types across Nova 1.0 and 2.0 models.
Docs: https://docs.aws.amazon.com/nova/latest/userguide/customize-fine-tune-prepare.html
    """
    parser = argparse.ArgumentParser(
        description=description, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-i", "--input_file", type=str, required=True,
        help="Path to the training JSONL file",
    )
    parser.add_argument(
        "--validation", type=str, default=None,
        help="Path to the validation JSONL file (optional)",
    )
    parser.add_argument(
        "-m", "--model_name", type=str, required=True,
        choices=["micro", "micro-1.0", "lite", "lite-1.0", "lite-2.0", "pro", "pro-1.0"],
        help="Model name",
    )
    parser.add_argument(
        "-t", "--task_type", type=str, default="sft",
        choices=["sft", "cpt", "dpo", "rft"],
        help="Task type: sft, cpt, dpo, rft (default: sft)",
    )
    parser.add_argument(
        "-p", "--platform", type=str, default="bedrock",
        choices=["bedrock", "sagemaker"],
        help="Platform: bedrock or sagemaker (default: bedrock)",
    )
    parser.add_argument(
        "--skip-bad-samples", action="store_true", default=False,
        help="Continue past bad samples to report all issues in one pass",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    task_type = TaskType(args.task_type.upper())

    # --- Validate training file ---
    print(f"Validating training file: {args.input_file}")
    train_report = validate_jsonl_file(
        args.input_file, args.model_name, task_type,
        platform=args.platform, skip_bad_samples=args.skip_bad_samples,
    )

    # --- Validate validation file (if provided) ---
    val_report = None
    if args.validation:
        print(f"Validating validation file: {args.validation}")
        val_report = validate_jsonl_file(
            args.validation, args.model_name, task_type,
            platform=args.platform, skip_bad_samples=args.skip_bad_samples,
        )

    # --- Dataset-level checks (only for bedrock) ---
    dataset_errors: List[str] = []
    if args.platform.lower() == "bedrock":
        dataset_errors = validate_dataset_level(
            train_report, val_report, args.model_name, args.task_type,
        )

    # --- Print reports ---
    print(train_report.summary())
    if val_report:
        print(val_report.summary())

    if dataset_errors:
        print("\nDataset-level issues:")
        for err in dataset_errors:
            print(f"  - {err}")

    # --- Exit code ---
    has_errors = (
        train_report.failed_samples > 0
        or (val_report is not None and val_report.failed_samples > 0)
        or len(dataset_errors) > 0
    )

    if has_errors:
        print("\nResult: FAIL — please fix the issues above and re-validate.")
        return 1
    else:
        print("\nResult: PASS — dataset is valid for Nova fine-tuning.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
