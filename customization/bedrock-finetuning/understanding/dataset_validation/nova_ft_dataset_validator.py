import argparse
import json
import re
from enum import Enum
from typing import Annotated, List, Optional, Union, cast

from pydantic import (
    BaseModel,
    Discriminator,
    Tag,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

IMAGE_FORMATS = ["jpeg", "png", "gif", "webp"]
VIDEO_FORMATS = ["mov", "mkv", "mp4", "webm"]
DOCUMENT_FORMATS = ["pdf"]
# Nova 2.0 Lite restricted formats
NOVA_2_0_LITE_IMAGE_FORMATS = ["png", "jpeg", "gif"]
NOVA_2_0_LITE_VIDEO_FORMATS = ["mov", "mkv", "mp4"]
NOVA_2_0_LITE_DOCUMENT_FORMATS = ["pdf"]
MAX_NUM_IMAGES = 10
MODEL_TO_NUM_SAMPLES_MAP = {
    "micro": (8, 20000),
    "micro-1.0": (8, 20000),
    "lite": (8, 20000),
    "lite-1.0": (8, 20000),
    "lite-2.0": (8, 20000),
    "pro": (8, 20000),
    "pro-1.0": (8, 20000),
}

# Nova 2.0 Lite specific sample bounds by task type
NOVA_2_0_LITE_SAMPLE_BOUNDS = {
    "SFT": (200, 20000),
    "DPO": (8, 20000),
    "RFT": (100, 20000),
}

# Models that support reasoning content (Nova 2.0 Lite only)
REASONING_SUPPORTED_MODELS = ["lite-2.0"]

INVALID_TOKENS_TEXT = [
    "System:",
    "SYSTEM:",
    "User:",
    "USER:",
    "Bot:",
    "BOT:",
    "Assistant:",
    "ASSISTANT:",
    "Thought:",
    "[EOS]",
    "<image>",
    "<video>",
    "<unk>",
]


class PreferenceLabels:
    PREFERRED = "preferred"
    NON_PREFERRED = "non-preferred"


# Converse message with a preferred and non-preferred model output for DPO
PREFERENCE_LABELS = [PreferenceLabels.PREFERRED, PreferenceLabels.NON_PREFERRED]


class TaskType(Enum):
    SFT = "SFT"
    DPO = "DPO"
    RFT = "RFT"


class ConverseRoles:
    """Defines the possible roles in a conversation according to converse format"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


CONVERSE_ROLES_WITHOUT_SYSTEM = [ConverseRoles.USER, ConverseRoles.ASSISTANT]


class NovaClientError(ValueError):
    """Custom exception for Nova client validation errors."""

    def __init__(self, message):
        super().__init__(message)


class NovaInternalError(Exception):
    """Base exception for Nova Fine Tuning validation errors"""

    pass


def check_jsonl_file(file_path):
    """Validates that the input file has a .jsonl extension."""
    if not file_path.endswith(".jsonl"):
        raise NovaClientError(f"File is not jsonl: {file_path}")


def load_jsonl_data(file_path: str):
    """Loads and validates JSON lines from the specified file path."""
    try:
        check_jsonl_file(file_path)
        data = []
        with open(file_path, "r") as file:
            for line_number, line in enumerate(file, 1):
                try:
                    parsed_line = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Line {line_number}: Invalid JSON syntax - {str(e)}\nLine content: {line}"
                    )
                data.append(parsed_line)
        return data
    except Exception as e:
        raise NovaClientError(f"Error loading data from {file_path}: {str(e)}")


class S3Location(BaseModel):
    """Represents and validates an S3 URI location."""

    uri: str
    bucketOwner: Optional[str] = None

    @field_validator("uri")
    def validate_format(cls, uri):
        """Validates that the URI starts with 's3://'."""
        if not uri.startswith("s3://"):
            raise ValueError("Invalid S3 URI, must start with 's3://'")
        is_valid_path(uri.replace("s3://", ""))
        return uri


class Source(BaseModel):
    """Defines the source location for media content."""

    s3Location: S3Location


class ImageContent(BaseModel):
    """Represents and validates image content with format and source."""

    format: str
    source: Source

    @field_validator("format")
    def validate_format(cls, image_format):
        """Validates that the image format is supported."""
        if image_format.lower() not in IMAGE_FORMATS:
            raise ValueError(f"Invalid image format, supported formats are {IMAGE_FORMATS}")
        return image_format


class VideoContent(BaseModel):
    """Represents and validates video content with format and source."""

    format: str
    source: Source

    @field_validator("format")
    def validate_format(cls, video_format):
        """Validates that the video format is supported."""
        if video_format.lower() not in VIDEO_FORMATS:
            raise ValueError(f"Invalid video format, supported formats are {VIDEO_FORMATS}")
        return video_format


class DocumentContent(BaseModel):
    """Represents and validates document content with format and source."""

    format: str
    source: Source

    @field_validator("format")
    def validate_format(cls, document_format):
        """Validates that the document format is supported."""
        if document_format.lower() not in DOCUMENT_FORMATS:
            raise ValueError(f"Invalid document format, supported formats are {DOCUMENT_FORMATS}")
        return document_format


class ReasoningText(BaseModel):
    """Represents reasoning text content for Nova 2.0."""

    text: str

    @field_validator("text")
    def validate_text(cls, text: str):
        if not text:
            raise ValueError("Invalid reasoningText, text field cannot be empty")
        validate_invalid_tokens(text)
        return text


class ReasoningContent(BaseModel):
    """Represents reasoning content structure for Nova 2.0."""

    reasoningText: ReasoningText

    @field_validator("reasoningText")
    def validate_reasoning_text(cls, reasoning_text):
        if reasoning_text is None:
            raise ValueError("Invalid reasoningContent, reasoningText field is required")
        return reasoning_text


class InputSchema(BaseModel):
    """Represents the input schema for a tool."""

    json: dict

    @field_validator("json")
    def validate_json_schema(cls, schema):
        """Validates that the schema is a valid object."""
        if not isinstance(schema, dict):
            raise ValueError("Invalid inputSchema, json field must be a valid JSON Schema object")
        # Basic JSON Schema validation
        if "type" not in schema:
            raise ValueError("Invalid inputSchema, json must have a 'type' field")
        return schema


class ToolSpec(BaseModel):
    """Represents a tool specification."""

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
    """Represents a tool with its specification."""

    toolSpec: ToolSpec


class ToolConfig(BaseModel):
    """Represents the tool configuration for a conversation."""

    tools: List[Tool]

    @field_validator("tools")
    def validate_tools(cls, tools):
        if not tools:
            raise ValueError("Invalid toolConfig, tools list cannot be empty")
        # Check for duplicate tool names
        tool_names = [tool.toolSpec.name for tool in tools]
        if len(tool_names) != len(set(tool_names)):
            raise ValueError("Invalid toolConfig, duplicate tool names found")
        return tools


class ToolUse(BaseModel):
    """Represents a tool use request from the assistant."""

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
    """Represents content within a tool result."""

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
    """Represents the result of a tool execution."""

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


class ContentItem(BaseModel):
    """Represents a content item that can contain text, image, video, document, reasoning content, toolUse, or toolResult (Nova 2.0)."""

    text: Optional[str] = None
    image: Optional[ImageContent] = None
    video: Optional[VideoContent] = None
    document: Optional[DocumentContent] = None
    reasoningContent: Optional[ReasoningContent] = None
    toolUse: Optional[ToolUse] = None
    toolResult: Optional[ToolResult] = None

    @model_validator(mode="after")
    def validate_model_fields(cls, values):
        """Validates that at least one content type is provided."""
        if not any(getattr(values, field) is not None for field in cls.model_fields.keys()):
            raise ValueError(
                f"Invalid content, at least one of {list(cls.model_fields.keys())} must be provided"
            )
        
        # Validate that reasoningContent cannot coexist with image or video
        if values.reasoningContent is not None:
            if values.image is not None or values.video is not None:
                raise ValueError(
                    "Invalid content, reasoningContent cannot be used with image or video content"
                )
        
        # Validate that toolUse and toolResult cannot coexist in the same ContentItem
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


class CandidateItem(BaseModel):
    content: List[ContentItem]
    preferenceLabel: str

    @field_validator("content")
    def validate_content(cls, content):
        has_video = any(item.video is not None for item in content)
        has_image = any(item.image is not None for item in content)
        has_reasoning = any(item.reasoningContent is not None for item in content)

        if has_video or has_image:
            raise ValueError("Invalid content, candidate contents cannot include image/video")

        # Check if there's any text content (reasoning content alone is valid)
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
        """Validates that the role is either user or assistant."""
        validate_role_name(role)
        return role

    @field_validator("candidates")
    def validate_candidates(cls, candidates):
        if len(candidates) < 2:
            raise ValueError("Invalid candidates, candidates list must have at least two items")

        preference_labels = set(candidate.preferenceLabel for candidate in candidates)
        if len(preference_labels) < 2:
            raise ValueError(
                "Invalid candidates, all candidates cannot have the same preferenceLabel"
            )

        return candidates


class Message(BaseModel):
    """Represents a conversation message with role and content."""

    role: str
    content: List[ContentItem]

    @field_validator("role")
    def validate_role(cls, role):
        """Validates that the role is either user or assistant."""
        validate_role_name(role)
        return role

    @model_validator(mode="after")
    def validate_content_rules(cls, values):
        """Validates content rules for assistant messages."""
        content_items = values.content
        has_video = any(item.video is not None for item in content_items)
        has_image = any(item.image is not None for item in content_items)
        has_reasoning = any(item.reasoningContent is not None for item in content_items)

        if has_image or has_video:
            if values.role.lower() == "assistant":
                raise ValueError(
                    "Invalid content, image/video cannot be included when role is 'assistant'"
                )

        # Validate that reasoningContent can only be used in assistant messages
        if has_reasoning:
            if values.role.lower() != "assistant":
                raise ValueError(
                    "Invalid content, reasoningContent can only be included in assistant messages"
                )

        return values

    @field_validator("content")
    def validate_content(cls, content, info: ValidationInfo):
        """Validates message content against Nova's rules for text, images, videos, and reasoning.
        Ensures content follows size limits (max 10 images, 1 video), format restrictions,
        and model-specific constraints (no media for micro models, reasoning for Nova 2.0).
        Checks that text content is not empty and media types don't mix.

        Args:
            content (List[ContentItem]): List of content items to validate
            info (ValidationInfo): Validation context with model_name

        Raises:
            ValueError: If content violates Nova's rules
            Exception: If validation context is missing
        """
        has_text = any(item.text is not None for item in content)
        has_video = any(item.video is not None for item in content)
        has_image = any(item.image is not None for item in content)
        has_reasoning = any(item.reasoningContent is not None for item in content)

        total_text_length = sum(len(item.text) for item in content if item.text is not None)
        # Allow empty text content if reasoning content is present
        if has_text and not (has_image or has_video or has_reasoning) and total_text_length == 0:
            raise ValueError("Invalid content, empty text content")

        if not info.context:
            raise NovaInternalError("context is not set for validating model type")

        model_name = info.context["model_name"]
        is_micro_model = "micro" in model_name
        if is_micro_model and (has_image or has_video):
            raise ValueError(
                "Invalid content, image/video samples not supported by Nova Micro model"
            )
        
        # Reasoning content is only supported for Nova 2.0 Lite
        if has_reasoning:
            if model_name not in REASONING_SUPPORTED_MODELS:
                raise ValueError(
                    f"Invalid content, reasoning samples are only supported by Nova 2.0 Lite. "
                    f"Model '{model_name}' does not support reasoning. Use 'lite-2.0' for reasoning support."
                )

        # Validate image/video formats for lite-2.0
        if model_name == "lite-2.0":
            # Check image formats
            for item in content:
                if item.image is not None:
                    if item.image.format.lower() not in NOVA_2_0_LITE_IMAGE_FORMATS:
                        raise ValueError(
                            f"Invalid image format '{item.image.format}' for lite-2.0. "
                            f"Supported formats: {', '.join(NOVA_2_0_LITE_IMAGE_FORMATS)}"
                        )
            # Check video formats
            for item in content:
                if item.video is not None:
                    if item.video.format.lower() not in NOVA_2_0_LITE_VIDEO_FORMATS:
                        raise ValueError(
                            f"Invalid video format '{item.video.format}' for lite-2.0. "
                            f"Supported formats: {', '.join(NOVA_2_0_LITE_VIDEO_FORMATS)}"
                        )

        if sum(1 for item in content if item.video is not None) > 1:
            raise ValueError("Only one video is allowed per sample")

        if has_video and has_image:
            raise ValueError(
                "'content' list cannot contain both video items and image items for a given sample"
            )

        num_images = sum(1 for item in content if item.image is not None)
        if num_images > MAX_NUM_IMAGES:
            raise ValueError(
                f"Invalid content, number of images {num_images} exceed maximum allowed limit of {MAX_NUM_IMAGES}"
            )

        return content


class SystemMessage(BaseModel):
    """Represents a system message with text content."""

    text: str

    @field_validator("text")
    def validate_text(cls, text: str):
        if not text:
            return text

        validate_invalid_tokens(text)
        return text


class ConverseDatasetSample(BaseModel):
    """Represents a complete conversation sample with system message and message turns."""

    schemaVersion: Optional[str] = None
    system: Optional[List[SystemMessage]] = None
    toolConfig: Optional[ToolConfig] = None
    messages: List[Message]

    @field_validator("messages")
    def validate_data_sample_rules(cls, messages):
        """Validates the order and structure of messages in the conversation."""
        check_roles_order(messages)
        return messages

    @model_validator(mode="after")
    def validate_tool_use_rules(cls, values):
        """Validates tool use rules across the conversation."""
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

        check_roles_order(messages)

        return messages


# RFT (Reinforcement Fine-Tuning) Models
class RFTFunctionParameters(BaseModel):
    """Represents parameters for an RFT function."""
    
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
    """Represents an RFT function specification."""
    
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
    """Represents an RFT tool."""
    
    type: str
    function: RFTFunction
    
    @field_validator("type")
    def validate_type(cls, tool_type):
        if tool_type != "function":
            raise ValueError("Invalid tool type, must be 'function'")
        return tool_type


class RFTMessage(BaseModel):
    """Represents a simple RFT message with optional role and content per RFT specification."""
    
    role: Optional[str] = None
    content: Optional[str] = None
    
    @field_validator("role")
    def validate_role(cls, role):
        # role is optional, but if provided must be valid
        if role is not None:
            valid_roles = ["system", "user", "assistant"]
            if role.lower() not in valid_roles:
                raise ValueError(f"Invalid role, must be one of {valid_roles}")
        return role
    
    @field_validator("content")
    def validate_content(cls, content):
        # content is optional, but if provided must not be empty
        if content is not None:
            if not content.strip():
                raise ValueError("Invalid content, if provided cannot be empty")
            validate_invalid_tokens(content)
        return content


class RFTDatasetSample(BaseModel):
    """Represents an RFT dataset sample with required messages and tools, optional id and reference answer.
    
    Field requirements per RFT specification:
    - id: Optional - Unique identifier for tracking
    - messages: Required - Array of message objects
    - messages[].role: Optional - "system", "user", or "assistant"
    - messages[].content: Optional - Text content of the message
    - tools: Required - Tool specifications available to the model
    - reference_answer: Optional - Expected output (string or object)
    """
    
    id: Optional[str] = None
    messages: List[RFTMessage]
    tools: List[RFTTool]
    reference_answer: Optional[Union[str, dict]] = None
    
    @field_validator("id")
    def validate_id(cls, sample_id):
        # id is optional, but if provided must not be empty
        if sample_id is not None and (not sample_id or not sample_id.strip()):
            raise ValueError("Invalid id, if provided cannot be empty")
        return sample_id
    
    @field_validator("messages")
    def validate_messages(cls, messages):
        if not messages:
            raise ValueError("Invalid messages, cannot be empty")
        
        # Check that messages have valid role sequence if roles are provided
        has_system = any(msg.role.lower() == "system" for msg in messages if msg.role)
        if has_system:
            # If there's a system message, it should be first
            first_role = messages[0].role.lower() if messages[0].role else None
            if first_role != "system":
                raise ValueError("Invalid messages, system message must be first if present")
        
        # Check that there's at least one user message
        if not any(msg.role and msg.role.lower() == "user" for msg in messages):
            raise ValueError("Invalid messages, must have at least one user message")
        
        return messages
    
    @field_validator("reference_answer")
    def validate_reference_answer(cls, reference_answer):
        # reference_answer is optional, but if provided must not be empty
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
        # tools is required and cannot be empty
        if not tools:
            raise ValueError("Invalid tools, tools field is required and cannot be empty list")
        # Check for duplicate tool names
        tool_names = [tool.function.name for tool in tools]
        if len(tool_names) != len(set(tool_names)):
            raise ValueError("Invalid tools, duplicate tool names found")
        return tools


def validate_converse_dataset(args):
    """Validates the entire conversation dataset against Nova format requirements."""
    try:
        samples = load_jsonl_data(args.input_file)
        num_samples = len(samples)
        print(f"Loaded {num_samples} samples from {args.input_file}")
        
        # Only validate data record bounds for Bedrock platform
        if args.platform.lower() == "bedrock":
            print(f"Platform: {args.platform} - Validating data record bounds")
            validate_data_record_bounds(num_samples, args.model_name, args.task_type)
        else:
            print(f"Platform: {args.platform} - Skipping data record bounds validation")
    except Exception as e:
        print(f"Error loading or validating file bounds: {e}")
        raise

    error_message = ""
    failed_samples_id_list = []

    print(f"Validating samples for model: {args.model_name}")
    task_type = TaskType(str(args.task_type).upper())
    print(f"Using task: {task_type}")
    
    # RFT is only supported on lite-2.0
    if task_type is TaskType.RFT and args.model_name != "lite-2.0":
        raise NovaClientError(
            f"RFT task type is only supported on lite-2.0 model. "
            f"Current model: {args.model_name}. Please use -m lite-2.0 for RFT tasks."
        )
    
    for i, sample in enumerate(samples):
        try:
            if task_type is TaskType.RFT:
                RFTDatasetSample.model_validate(sample)
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
                sample_error_message = (
                    f"  - Location {err['loc']}: {err['msg']} (type={err['type']})\n"
                )
                error_message += sample_error_message
        except Exception as e:
            raise NovaInternalError(f"Unexpected error occurred in sample {i}: {e}")

    if error_message:

        if len(failed_samples_id_list) > 3:
            first_sample_id = failed_samples_id_list[0]
            second_sample_id = failed_samples_id_list[1]
            last_sample_id = failed_samples_id_list[-1]
            failed_samples_str = f"[{first_sample_id}, {second_sample_id}, ...{last_sample_id}]"
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


def validate_invalid_tokens(text: str):
    """Validates that the input text does not contain any disallowed tokens"""

    stripped_text = text.strip()
    client_invalid_tokens = []
    for invalid_token in INVALID_TOKENS_TEXT:
        if invalid_token in stripped_text:
            client_invalid_tokens.append(f"`{invalid_token}`")

    if client_invalid_tokens:
        client_invalid_tokens_str = ", ".join(client_invalid_tokens)
        raise ValueError(
            f"Invalid text content, following tokens are invalid: {client_invalid_tokens_str}. Please check documentation for other invalid tokens"
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
