"""Event templates for Bedrock streaming."""
import json
from typing import Dict, Any, List
from src.core.config import MAX_TOKENS, TOP_P, TEMPERATURE, INPUT_SAMPLE_RATE, OUTPUT_SAMPLE_RATE


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
    def prompt_start(prompt_name: str, voice_id: str, active_agent: str, tools: List[Dict[str, Any]]) -> str:
        """Create prompt start event with tool configuration."""
        agent_tools = {
            "support": {
                "name": "open_ticket_tool",
                "description": "Create a support ticket for customer issues",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "issue_description": {"type": "string", "description": "Description of the customer's issue"},
                            "customer_name": {"type": "string", "description": "Name of the customer"}
                        },
                        "required": ["issue_description", "customer_name"]
                    })
                }
            },
            "sales": {
                "name": "order_computers_tool",
                "description": "Place an order for computers",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "computer_type": {"type": "string", "description": "Type of computer", "enum": ["laptop", "desktop"]},
                            "customer_name": {"type": "string", "description": "Name of the customer"}
                        },
                        "required": ["computer_type", "customer_name"]
                    })
                }
            },
            "tracking": {
                "name": "check_order_location_tool",
                "description": "Check order location and status",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "order_id": {"type": "string", "description": "Order ID to check"},
                            "customer_name": {"type": "string", "description": "Name of the customer"}
                        },
                        "required": ["order_id", "customer_name"]
                    })
                }
            }
        }
        
        tool_list = [
            {
                "toolSpec": {
                    "name": "switch_agent",
                    "description": "CRITICAL: Invoke this function IMMEDIATELY when user requests to switch personas, speak with another department, or needs a different type of assistance. This transfers the conversation to a specialized agent with appropriate tools and expertise. Available agents: 'support' (technical issues, complaints, problems - creates support tickets), 'sales' (purchasing, pricing, product info - processes orders), 'tracking' (order status, delivery updates - checks shipment location). Example inputs - Sales requests: 'Can I buy a computer?', 'How much does a laptop cost?', 'I want to purchase a desktop', 'What products do you sell?', 'I'd like to place an order'. Support requests: 'I have issues with my wifi', 'My computer won't turn on', 'I need help with a problem', 'Something is broken', 'I want to file a complaint'. Tracking requests: 'What's my order status?', 'Where is my delivery?', 'When will my order arrive?', 'Can you track my package?', 'Has my order shipped yet?'. Direct transfer requests: 'Let me speak with sales', 'Transfer me to support', 'I need to talk to tracking'.",
                    "inputSchema": {
                        "json": json.dumps({
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["support", "sales", "tracking"], "default": "support"}
                            },
                            "required": ["role"]
                        })
                    }
                }
            }
        ]
        
        if active_agent in agent_tools:
            tool_list.append({"toolSpec": agent_tools[active_agent]})
        
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
                    "toolConfiguration": {"tools": tool_list}
                }
            }
        })
