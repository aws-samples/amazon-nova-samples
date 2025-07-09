"""
For Input Events documenationt see: https://docs.aws.amazon.com/nova/latest/userguide/input-events.html
For Output Events documenationt see: https://docs.aws.amazon.com/nova/latest/userguide/output-events.html
"""

# Most events here are not used directly from the python backend.
# They instead are directly generated from the frontend and just passed-through to Sonic.

class SonicEvent:
    DEFAULT_INFER_CONFIG = {
        "maxTokens": 1024,
        "temperature": 0.5,
        "topP": 0.95,
    }

    DEFAULT_SYSTEM_PROMPT = "You are a friendly assistant. The user and you will engage in a spoken dialog " \
    "exchanging the transcripts of a natural real-time conversation. Keep your responses short, " \
    "generally one or two sentences for chatty scenarios. If you get interrupted, only reply with 'Ok' and nothing else."

    DEFAULT_AUDIO_INPUT_CONFIG = {
        "mediaType": "audio/lpcm",
        "sampleRateHertz": 16000,
        "sampleSizeBits": 16,
        "channelCount": 1,
        "audioType": "SPEECH",
        "encoding": "base64",
    }

    DEFAULT_AUDIO_OUTPUT_CONFIG = {
        "mediaType": "audio/lpcm",
        "sampleRateHertz": 24000,
        "sampleSizeBits": 16,
        "channelCount": 1,
        "voiceId": "matthew",
        "encoding": "base64",
        "audioType": "SPEECH",
    }

    DEFAULT_TOOL_CONFIG = { "tools": [] }

    @staticmethod
    def session_start(inference_config=DEFAULT_INFER_CONFIG):
        return {
            "event": {
                "sessionStart": {
                    "inferenceConfiguration": inference_config,
                }
            }
        }

    @staticmethod
    def prompt_start(
        prompt_name,
        audio_output_config=DEFAULT_AUDIO_OUTPUT_CONFIG,
        tool_config=DEFAULT_TOOL_CONFIG,
    ):
        return {
            "event": {
                "promptStart": {
                    "promptName": prompt_name,
                    "textOutputConfiguration": {"mediaType": "text/plain"},
                    "audioOutputConfiguration": audio_output_config,
                    "toolUseOutputConfiguration": {"mediaType": "application/json"},
                    "toolConfiguration": tool_config,
                }
            }
        }

    @staticmethod
    def content_start_text(prompt_name, content_name):
        return {
            "event": {
                "contentStart": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "type": "TEXT",
                    "interactive": True,
                    "role": "SYSTEM",
                    "textInputConfiguration": {"mediaType": "text/plain"},
                }
            }
        }

    @staticmethod
    def text_input(prompt_name, content_name, content=DEFAULT_SYSTEM_PROMPT):
        return {
            "event": {
                "textInput": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "content": content,
                }
            }
        }

    @staticmethod
    def content_end(prompt_name, content_name):
        return {
            "event": {
                "contentEnd": {"promptName": prompt_name, "contentName": content_name}
            }
        }

    @staticmethod
    def content_start_audio(
        prompt_name, content_name, audio_input_config=DEFAULT_AUDIO_INPUT_CONFIG
    ):
        return {
            "event": {
                "contentStart": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "type": "AUDIO",
                    "interactive": True,
                    "audioInputConfiguration": audio_input_config,
                }
            }
        }

    @staticmethod
    def audio_input(prompt_name, content_name, content):
        return {
            "event": {
                "audioInput": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "content": content,
                }
            }
        }

    @staticmethod
    def content_start_tool(prompt_name, content_name, tool_use_id):
        return {
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
                        "textInputConfiguration": {"mediaType": "text/plain"},
                    },
                }
            }
        }

    @staticmethod
    def text_input_tool(prompt_name, content_name, content) -> dict:
        return {
            "event": {
                "toolResult": {
                    "promptName": prompt_name,
                    "contentName": content_name,
                    "content": content,
                }
            }
        }

    @staticmethod
    def prompt_end(prompt_name):
        return {
            "event": {
                "promptEnd": {
                    "promptName": prompt_name}
            }
        }

    @staticmethod
    def session_end():
        return {
            "event": {
                "sessionEnd": {}
            }
        }
