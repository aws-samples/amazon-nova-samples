"""Typed event dataclasses for Bedrock stream responses."""
from dataclasses import dataclass
from typing import Dict, Any, Optional, Union


@dataclass
class CompletionStartEvent:
    data: Dict[str, Any]


@dataclass
class ContentStartEvent:
    role: str
    is_final_response: bool = False


@dataclass
class TextOutputEvent:
    content: str
    role: str


@dataclass
class AudioOutputEvent:
    audio_base64: str


@dataclass
class ToolUseEvent:
    tool_name: str
    tool_use_id: str
    content: Dict[str, Any]


@dataclass
class BargeInEvent:
    pass


@dataclass
class ContentEndEvent:
    content_type: Optional[str] = None


@dataclass
class CompletionEndEvent:
    pass


@dataclass
class UsageEvent:
    data: Dict[str, Any]


@dataclass
class UnknownEvent:
    raw_data: str


StreamEvent = Union[
    CompletionStartEvent,
    ContentStartEvent,
    TextOutputEvent,
    AudioOutputEvent,
    ToolUseEvent,
    BargeInEvent,
    ContentEndEvent,
    CompletionEndEvent,
    UsageEvent,
    UnknownEvent,
]
