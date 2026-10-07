"""Unit tests for ResponseParser covering each event type, malformed JSON, and missing fields."""
import json
import pytest

from src.connection.response_parser import ResponseParser
from src.connection.stream_events import (
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


# --- completionStart ---

class TestCompletionStart:
    def test_basic(self):
        data = json.dumps({"event": {"completionStart": {"requestId": "abc123"}}})
        result = ResponseParser.parse(data)
        assert isinstance(result, CompletionStartEvent)
        assert result.data["completionStart"]["requestId"] == "abc123"


# --- contentStart ---

class TestContentStart:
    def test_basic_role(self):
        data = json.dumps({"event": {"contentStart": {"role": "ASSISTANT"}}})
        result = ResponseParser.parse(data)
        assert isinstance(result, ContentStartEvent)
        assert result.role == "ASSISTANT"
        assert result.is_final_response is False

    def test_final_response(self):
        data = json.dumps({
            "event": {
                "contentStart": {
                    "role": "ASSISTANT",
                    "additionalModelFields": json.dumps({"generationStage": "FINAL"}),
                }
            }
        })
        result = ResponseParser.parse(data)
        assert isinstance(result, ContentStartEvent)
        assert result.is_final_response is True

    def test_non_final_generation_stage(self):
        data = json.dumps({
            "event": {
                "contentStart": {
                    "role": "ASSISTANT",
                    "additionalModelFields": json.dumps({"generationStage": "SPECULATIVE"}),
                }
            }
        })
        result = ResponseParser.parse(data)
        assert isinstance(result, ContentStartEvent)
        assert result.is_final_response is False

    def test_malformed_additional_fields(self):
        data = json.dumps({
            "event": {
                "contentStart": {
                    "role": "USER",
                    "additionalModelFields": "not-valid-json{",
                }
            }
        })
        result = ResponseParser.parse(data)
        assert isinstance(result, ContentStartEvent)
        assert result.role == "USER"
        assert result.is_final_response is False

    def test_missing_role(self):
        data = json.dumps({"event": {"contentStart": {}}})
        result = ResponseParser.parse(data)
        assert isinstance(result, ContentStartEvent)
        assert result.role == ""


# --- textOutput ---

class TestTextOutput:
    def test_basic(self):
        data = json.dumps({
            "event": {"textOutput": {"content": "Hello!", "role": "ASSISTANT"}}
        })
        result = ResponseParser.parse(data)
        assert isinstance(result, TextOutputEvent)
        assert result.content == "Hello!"
        assert result.role == "ASSISTANT"

    def test_barge_in(self):
        data = json.dumps({
            "event": {
                "textOutput": {
                    "content": '{ "interrupted" : true }',
                    "role": "ASSISTANT",
                }
            }
        })
        result = ResponseParser.parse(data)
        assert isinstance(result, BargeInEvent)

    def test_barge_in_embedded(self):
        data = json.dumps({
            "event": {
                "textOutput": {
                    "content": 'some text { "interrupted" : true } more text',
                    "role": "ASSISTANT",
                }
            }
        })
        result = ResponseParser.parse(data)
        assert isinstance(result, BargeInEvent)

    def test_missing_fields(self):
        data = json.dumps({"event": {"textOutput": {}}})
        result = ResponseParser.parse(data)
        assert isinstance(result, TextOutputEvent)
        assert result.content == ""
        assert result.role == ""


# --- audioOutput ---

class TestAudioOutput:
    def test_basic(self):
        data = json.dumps({
            "event": {"audioOutput": {"content": "base64audiodata=="}}
        })
        result = ResponseParser.parse(data)
        assert isinstance(result, AudioOutputEvent)
        assert result.audio_base64 == "base64audiodata=="

    def test_missing_content(self):
        data = json.dumps({"event": {"audioOutput": {}}})
        result = ResponseParser.parse(data)
        assert isinstance(result, AudioOutputEvent)
        assert result.audio_base64 == ""


# --- toolUse ---

class TestToolUse:
    def test_basic(self):
        tool_content = json.dumps({"role": "sales"})
        data = json.dumps({
            "event": {
                "toolUse": {
                    "toolName": "switch_agent",
                    "toolUseId": "tool-123",
                    "content": tool_content,
                }
            }
        })
        result = ResponseParser.parse(data)
        assert isinstance(result, ToolUseEvent)
        assert result.tool_name == "switch_agent"
        assert result.tool_use_id == "tool-123"
        assert result.content == {"role": "sales"}

    def test_non_switch_tool(self):
        tool_content = json.dumps({"order_id": "ORD-456"})
        data = json.dumps({
            "event": {
                "toolUse": {
                    "toolName": "track_order",
                    "toolUseId": "tool-789",
                    "content": tool_content,
                }
            }
        })
        result = ResponseParser.parse(data)
        assert isinstance(result, ToolUseEvent)
        assert result.tool_name == "track_order"
        assert result.content == {"order_id": "ORD-456"}

    def test_malformed_content(self):
        data = json.dumps({
            "event": {
                "toolUse": {
                    "toolName": "some_tool",
                    "toolUseId": "id-1",
                    "content": "not-valid-json{",
                }
            }
        })
        result = ResponseParser.parse(data)
        assert isinstance(result, ToolUseEvent)
        assert result.content == {}

    def test_dict_content(self):
        """Content already a dict (not a JSON string)."""
        data = json.dumps({
            "event": {
                "toolUse": {
                    "toolName": "my_tool",
                    "toolUseId": "id-2",
                    "content": {"key": "value"},
                }
            }
        })
        result = ResponseParser.parse(data)
        assert isinstance(result, ToolUseEvent)
        assert result.content == {"key": "value"}

    def test_missing_fields(self):
        data = json.dumps({"event": {"toolUse": {}}})
        result = ResponseParser.parse(data)
        assert isinstance(result, ToolUseEvent)
        assert result.tool_name == ""
        assert result.tool_use_id == ""
        assert result.content == {}


# --- contentEnd ---

class TestContentEnd:
    def test_with_type(self):
        data = json.dumps({"event": {"contentEnd": {"type": "TOOL"}}})
        result = ResponseParser.parse(data)
        assert isinstance(result, ContentEndEvent)
        assert result.content_type == "TOOL"

    def test_without_type(self):
        data = json.dumps({"event": {"contentEnd": {}}})
        result = ResponseParser.parse(data)
        assert isinstance(result, ContentEndEvent)
        assert result.content_type is None


# --- completionEnd ---

class TestCompletionEnd:
    def test_basic(self):
        data = json.dumps({"event": {"completionEnd": {}}})
        result = ResponseParser.parse(data)
        assert isinstance(result, CompletionEndEvent)


# --- usageEvent ---

class TestUsageEvent:
    def test_basic(self):
        data = json.dumps({
            "event": {
                "usageEvent": {"inputTokens": 100, "outputTokens": 50}
            }
        })
        result = ResponseParser.parse(data)
        assert isinstance(result, UsageEvent)
        assert result.data["usageEvent"]["inputTokens"] == 100


# --- UnknownEvent / error cases ---

class TestUnknownEvent:
    def test_invalid_json(self):
        result = ResponseParser.parse("not json at all {{{")
        assert isinstance(result, UnknownEvent)
        assert result.raw_data == "not json at all {{{"

    def test_empty_string(self):
        result = ResponseParser.parse("")
        assert isinstance(result, UnknownEvent)

    def test_valid_json_no_event_key(self):
        data = json.dumps({"something": "else"})
        result = ResponseParser.parse(data)
        assert isinstance(result, UnknownEvent)
        assert data in result.raw_data

    def test_unrecognized_event_type(self):
        data = json.dumps({"event": {"unknownType": {"data": 1}}})
        result = ResponseParser.parse(data)
        assert isinstance(result, UnknownEvent)

    def test_none_input(self):
        result = ResponseParser.parse(None)
        assert isinstance(result, UnknownEvent)
