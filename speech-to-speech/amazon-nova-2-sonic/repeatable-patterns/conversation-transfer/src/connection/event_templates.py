"""Event templates for Bedrock streaming."""
import json
from typing import Dict, Any, List
from src.config import MAX_TOKENS, TOP_P, TEMPERATURE, INPUT_SAMPLE_RATE, OUTPUT_SAMPLE_RATE


class EventTemplates:
    """Bedrock event template generator."""
    
    @staticmethod
    def start_session() -> str:
        """Create session start event."""
        return json.dumps({
            "event": {
                "sessionStart": {
                    "inferenceConfiguration": {
                        "maxTokens": MAX_TOKENS,
                        "topP": TOP_P,
                        "temperature": TEMPERATURE
                    }
                }
            }
        })
    
    @staticmethod
    def content_start(prompt_name: str, content_name: str, role: str = "USER") -> str:
        """Create audio content start event."""
        return json.dumps({
            "event": {
                "contentStart": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "type": "AUDIO",
                    "interactive": True,
                    "role": role,
                    "audioInputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": INPUT_SAMPLE_RATE,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "audioType": "SPEECH",
                        "encoding": "base64"
                    }
                }
            }
        })
    
    @staticmethod
    def audio_input(prompt_name: str, content_name: str, audio_base64: str) -> str:
        """Create audio input event."""
        return json.dumps({
            "event": {
                "audioInput": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "content": audio_base64
                }
            }
        })
    
    @staticmethod
    def text_content_start(prompt_name: str, content_name: str, role: str, interactive: bool = False) -> str:
        """Create text content start event."""
        return json.dumps({
            "event": {
                "contentStart": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "type": "TEXT",
                    "role": role,
                    "interactive": interactive,
                    "textInputConfiguration": {
                        "mediaType": "text/plain"
                    }
                }
            }
        })
    
    @staticmethod
    def text_input(prompt_name: str, content_name: str, content: str) -> str:
        """Create text input event."""
        return json.dumps({
            "event": {
                "textInput": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "content": content
                }
            }
        })
    
    @staticmethod
    def tool_content_start(prompt_name: str, content_name: str, tool_use_id: str) -> str:
        """Create tool content start event."""
        return json.dumps({
            "event": {
                "contentStart": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "interactive": False,
                    "type": "TOOL",
                    "role": "TOOL",
                    "toolResultInputConfiguration": {
                        "toolUseId": tool_use_id,
                        "type": "TEXT",
                        "textInputConfiguration": {
                            "mediaType": "text/plain"
                        }
                    }
                }
            }
        })
    
    @staticmethod
    def tool_result(prompt_name: str, content_name: str, content: Any) -> str:
        """Create tool result event."""
        content_str = json.dumps(content) if isinstance(content, dict) else str(content)
        return json.dumps({
            "event": {
                "toolResult": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "content": content_str
                }
            }
        })
    
    @staticmethod
    def content_end(prompt_name: str, content_name: str) -> str:
        """Create content end event."""
        return json.dumps({
            "event": {
                "contentEnd": {
                    "promptName": prompt_name,
                    "contentName": content_name
                }
            }
        })
    
    @staticmethod
    def prompt_end(prompt_name: str) -> str:
        """Create prompt end event."""
        return json.dumps({
            "event": {
                "promptEnd": {
                    "promptName": prompt_name
                }
            }
        })
    
    @staticmethod
    def session_end() -> str:
        """Create session end event."""
        return json.dumps({
            "event": {
                "sessionEnd": {}
            }
        })
    
    @staticmethod
    def prompt_start(prompt_name: str, voice_id: str, tool_schemas: List[Dict[str, Any]]) -> str:
        """Create prompt start event with tool configuration.
        
        Args:
            prompt_name: Name for the prompt.
            voice_id: Bedrock voice identifier.
            tool_schemas: Complete list of Bedrock-compatible tool schema dicts
                          (e.g. [{"toolSpec": {...}}, ...]). Passed through as-is.
        """
        return json.dumps({
            "event": {
                "promptStart": {
                    "promptName": prompt_name,
                    "textOutputConfiguration": {"mediaType": "text/plain"},
                    "audioOutputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": OUTPUT_SAMPLE_RATE,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "voiceId": voice_id,
                        "encoding": "base64",
                        "audioType": "SPEECH"
                    },
                    "toolUseOutputConfiguration": {"mediaType": "application/json"},
                    "toolConfiguration": {"tools": tool_schemas}
                }
            }
        })
