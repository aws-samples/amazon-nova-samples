"""Stateless parser that transforms raw Bedrock JSON into typed stream events."""
import json
from typing import Dict, Any

from src.connection.stream_events import (
    StreamEvent,
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
)


class ResponseParser:
    """Stateless transformer from raw Bedrock JSON to typed events.

    Contains no business logic — only protocol-level detection.
    """

    @staticmethod
    def parse(response_data: str) -> StreamEvent:
        """Parse a raw Bedrock JSON string into a typed StreamEvent."""
        try:
            json_data = json.loads(response_data)
        except (json.JSONDecodeError, TypeError):
            return UnknownEvent(raw_data=response_data)

        if "event" not in json_data:
            return UnknownEvent(raw_data=response_data)

        event = json_data["event"]

        if "completionStart" in event:
            return CompletionStartEvent(data=event)

        if "contentStart" in event:
            return ResponseParser._parse_content_start(event["contentStart"])

        if "textOutput" in event:
            return ResponseParser._parse_text_output(event["textOutput"])

        if "audioOutput" in event:
            return AudioOutputEvent(audio_base64=event["audioOutput"].get("content", ""))

        if "toolUse" in event:
            return ResponseParser._parse_tool_use(event["toolUse"])

        if "contentEnd" in event:
            return ContentEndEvent(content_type=event["contentEnd"].get("type"))

        if "completionEnd" in event:
            return CompletionEndEvent()

        if "usageEvent" in event:
            return UsageEvent(data=event)

        return UnknownEvent(raw_data=response_data)

    @staticmethod
    def _parse_content_start(content_start: Dict[str, Any]) -> ContentStartEvent:
        role = content_start.get("role", "")
        is_final = False
        if "additionalModelFields" in content_start:
            try:
                fields = json.loads(content_start["additionalModelFields"])
                is_final = fields.get("generationStage") == "FINAL"
            except (json.JSONDecodeError, TypeError):
                pass
        return ContentStartEvent(role=role, is_final_response=is_final)

    @staticmethod
    def _parse_text_output(text_output: Dict[str, Any]) -> StreamEvent:
        content = text_output.get("content", "")
        role = text_output.get("role", "")
        if '{ "interrupted" : true }' in content:
            return BargeInEvent()
        return TextOutputEvent(content=content, role=role)

    @staticmethod
    def _parse_tool_use(tool_use: Dict[str, Any]) -> ToolUseEvent:
        tool_name = tool_use.get("toolName", "")
        tool_use_id = tool_use.get("toolUseId", "")
        raw_content = tool_use.get("content", "{}")
        try:
            content = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
        except (json.JSONDecodeError, TypeError):
            content = {}
        return ToolUseEvent(tool_name=tool_name, tool_use_id=tool_use_id, content=content)
