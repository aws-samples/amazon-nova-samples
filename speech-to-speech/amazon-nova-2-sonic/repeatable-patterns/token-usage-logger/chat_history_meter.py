import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

class Event:
    """Base class for all events in the chat history"""
    
    def __init__(self, timestamp: Optional[float] = None):
        self.timestamp = timestamp or datetime.now().timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement to_dict")

class UsageEvent(Event):
    """Represents a usage event with token metrics"""
    
    def __init__(
        self,
        completion_id: str,
        session_id: str,
        prompt_name: str,
        total_input_tokens: int,
        total_output_tokens: int,
        total_tokens: int,
        details: Dict[str, Any],
        timestamp: Optional[float] = None
    ):
        super().__init__(timestamp)
        self.completion_id = completion_id
        self.session_id = session_id
        self.prompt_name = prompt_name
        self.total_input_tokens = total_input_tokens
        self.total_output_tokens = total_output_tokens
        self.total_tokens = total_tokens
        self.details = details
        self.type = "usage_event"
    
    def __str__(self) -> str:
        delta_info = ""
        if "delta" in self.details:
            delta = self.details["delta"]
            delta_info = f" (Delta - Input: {delta.get('input_tokens', 0)}, Output: {delta.get('output_tokens', 0)}, Total: {delta.get('total_tokens', 0)})"
        
        return f"Usage Event: {self.completion_id} - Input: {self.total_input_tokens}, Output: {self.total_output_tokens}, Total: {self.total_tokens}{delta_info}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "completion_id": self.completion_id,
            "session_id": self.session_id,
            "prompt_name": self.prompt_name,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "details": self.details,
            "timestamp": self.timestamp
        }

class ChatMessage(Event):
    """Base class for all chat messages"""
    
    def __init__(self, role: str, timestamp: Optional[float] = None):
        super().__init__(timestamp)
        self.role = role
    
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement to_dict")
    
class TextMessage(ChatMessage):
    """Represents a text message in the chat history"""
    
    def __init__(self, role: str, content: str, timestamp: Optional[float] = None):
        super().__init__(role, timestamp)
        self.content = content
        self.type = "text"

    def __str__(self) -> str:
        return f"{self.role}: {self.content}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }

class ToolCallMessage(ChatMessage):
    """Represents a tool call in the chat history"""
    
    def __init__(
        self, 
        tool_use_content: Any,
        timestamp: Optional[float] = None
    ):
        super().__init__("tool_call", timestamp)
        self.tool_use_content = tool_use_content
        self.type = "tool_call"

    def __str__(self) -> str:
        tool_use_content = json.dumps(self.tool_use_content, ensure_ascii=False) if self.tool_use_content else "{}"
        return f"Tool Call : {tool_use_content}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "tool_use_content": self.tool_use_content,
            "timestamp": self.timestamp
        }

class ToolResultMessage(ChatMessage):
    """Represents a tool result in the chat history"""
    
    def __init__(
        self, 
        tool_use_id: str, 
        result: Any,
        timestamp: Optional[float] = None
    ):
        super().__init__("tool_result", timestamp)
        self.tool_use_id = tool_use_id
        self.result = result
        self.type = "tool_result"

    def __str__(self) -> str:
        result_str = json.dumps(self.result, ensure_ascii=False) if self.result else "{}"
        return f"Tool Result: {result_str}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "tool_use_id": self.tool_use_id,
            "result": self.result,
            "timestamp": self.timestamp
        }

class ChatHistory:
    """Manages the conversation history including messages, tool interactions, and usage metrics"""
    
    def __init__(self):
        # All events in chronological order (messages and usage events)
        self.events: List[Event] = []
    
    def add_message(self, role: str, content: str) -> TextMessage:
        """Add a new text message to the chat history"""
        message = TextMessage(role, content)
        self.events.append(message)
        return message
    
    def add_tool_call(
        self, 
        tool_use_content: Any
    ) -> ToolCallMessage:
        """Add a tool call to the chat history"""
        message = ToolCallMessage(tool_use_content)
        self.events.append(message)
        return message
    
    def add_usage_event(
        self,
        completion_id: str,
        session_id: str,
        prompt_name: str,
        total_input_tokens: int,
        total_output_tokens: int,
        total_tokens: int,
        details: Dict[str, Any]
    ) -> UsageEvent:
        """Add a usage event to track token consumption"""
        usage_event = UsageEvent(
            completion_id=completion_id,
            session_id=session_id,
            prompt_name=prompt_name,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_tokens=total_tokens,
            details=details
        )
        self.events.append(usage_event)
        return usage_event
    
    def add_tool_result(
        self, 
        tool_use_id: str, 
        result: Any
    ) -> ToolResultMessage:
        """Add a tool result to the chat history"""
        message = ToolResultMessage(tool_use_id, result)
        self.events.append(message)
        return message
    
    def get_usage_events(self) -> List[UsageEvent]:
        """Get all usage events"""
        return [event for event in self.events if isinstance(event, UsageEvent)]
    
    def get_messages(self) -> List[ChatMessage]:
        """Get all chat messages"""
        return [event for event in self.events if isinstance(event, ChatMessage)]
    
    def get_token_usage_summary(self) -> Dict[str, Any]:
        """Get the token usage summary with both delta sum and final total"""
        usage_events = self.get_usage_events()
  

        if not usage_events:
            return {
                "delta_sum_calculated": {
                    "total_input_tokens": {
                        "speechTokens": 0,
                        "textTokens": 0,
                        "sum": 0
                    },
                    "total_output_tokens": {
                        "speechTokens": 0,
                        "textTokens": 0,
                        "sum": 0
                    },
                    "total_tokens": 0
                },
                "final_total": {
                    "total_input_tokens": {
                        "speechTokens": 0,
                        "textTokens": 0,
                        "sum": 0
                    },
                    "total_output_tokens": {
                        "speechTokens": 0,
                        "textTokens": 0,
                        "sum": 0
                    },
                    "total_tokens": 0
                },
                "final_total_sum": {
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_tokens": 0
                }
            }
        
        # Calculate sum of deltas
        delta_input_speech = 0
        delta_input_text = 0
        delta_output_speech = 0
        delta_output_text = 0
            
        
        for event in usage_events:
            if "delta" in event.details:
                delta = event.details["delta"]
                if ("input" in delta):
                    delta_input_speech += delta["input"].get("speechTokens", 0)
                    delta_input_text += delta["input"].get("textTokens", 0)
                if ("output" in delta):
                    delta_output_speech += delta["output"].get("speechTokens", 0)
                    delta_output_text += delta["output"].get("textTokens", 0)
        
        # Get final totals from the last usage event
        final_event = usage_events[-1]
        final_input_speech = 0
        final_input_text = 0
        final_output_speech = 0
        final_output_text = 0

            

        if "total" in final_event.details:
            final_event_total = final_event.details["total"]
            if ("input" in final_event_total):
                final_input_speech += final_event_total["input"].get("speechTokens", 0)
                final_input_text += final_event_total["input"].get("textTokens", 0)
            if ("output" in final_event_total):
                final_output_speech += final_event_total["output"].get("speechTokens", 0)
                final_output_text += final_event_total["output"].get("textTokens", 0)
        
        return {
            "delta_sum_calculated": {
                    "total_input_tokens": {
                        "speechTokens": delta_input_speech,
                        "textTokens": delta_input_text,
                        "sum": delta_input_speech + delta_input_text
                    },
                    "total_output_tokens": {
                        "speechTokens": delta_output_speech,
                        "textTokens": delta_output_text,
                        "sum": delta_output_speech + delta_output_text
                    },
                    "total_tokens": delta_input_speech + delta_input_text + delta_output_speech + delta_output_text
                },
            "final_total": {
                 "total_input_tokens": {
                        "speechTokens": final_input_speech,
                        "textTokens": final_input_text,
                        "sum": final_input_speech + final_input_text
                    },
                    "total_output_tokens": {
                        "speechTokens": final_output_speech,
                        "textTokens": final_output_text,
                        "sum": final_output_speech + final_output_text
                    },
                    "total_tokens": final_input_speech + final_input_text + final_output_speech + final_output_text
                },
            "final_total_sum": {
                    "total_input_tokens": final_event.total_input_tokens,
                    "total_output_tokens": final_event.total_output_tokens,
                    "total_tokens": final_event.total_tokens
                }
        }
    
    def get_full_history(self) -> str:
        """Get the full conversation history as a formatted string"""
        history_lines = []
        for event in self.events:
            history_lines.append(str(event))
        
        return "\n".join(history_lines)
    
    def get_last_n_events(self, n: int) -> List[Event]:
        """Get the last n events in the chat history"""
        return self.events[-n:] if n < len(self.events) else self.events.copy()
    
    def get_messages_by_role(self, role: str) -> List[ChatMessage]:
        """Get all messages with the specified role"""
        return [msg for msg in self.events if isinstance(msg, ChatMessage) and msg.role == role]
    
    def get_tool_calls(self) -> List[ToolCallMessage]:
        """Get all tool call messages"""
        return [msg for msg in self.events if isinstance(msg, ToolCallMessage)]
    
    def get_tool_results(self) -> List[ToolResultMessage]:
        """Get all tool result messages"""
        return [msg for msg in self.events if isinstance(msg, ToolResultMessage)]
    
    def clear(self) -> None:
        """Clear the chat history"""
        self.events.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the chat history to a dictionary"""
        return {
            "events": [event.to_dict() for event in self.events],
            "token_usage_summary": self.get_token_usage_summary()
        }
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """Convert the chat history to a JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatHistory':
        """Create a ChatHistory instance from a dictionary"""
        history = cls()
        
        # Load events
        for event_data in data.get("events", []):
            event_type = event_data.get("type", "")
            
            if event_type == "text":
                event = TextMessage(
                    event_data.get("role", ""),
                    event_data.get("content", ""),
                    event_data.get("timestamp")
                )
                history.events.append(event)
            elif event_type == "tool_call":
                event = ToolCallMessage(
                    event_data.get("tool_use_content", {}),
                    event_data.get("timestamp")
                )
                history.events.append(event)
            elif event_type == "tool_result":
                event = ToolResultMessage(
                    event_data.get("tool_use_id", ""),
                    event_data.get("result", {}),
                    event_data.get("timestamp")
                )
                history.events.append(event)
            elif event_type == "usage_event":
                event = UsageEvent(
                    completion_id=event_data.get("completion_id", ""),
                    session_id=event_data.get("session_id", ""),
                    prompt_name=event_data.get("prompt_name", ""),
                    total_input_tokens=event_data.get("total_input_tokens", 0),
                    total_output_tokens=event_data.get("total_output_tokens", 0),
                    total_tokens=event_data.get("total_tokens", 0),
                    details=event_data.get("details", {}),
                    timestamp=event_data.get("timestamp")
                )
                history.events.append(event)
                
        return history
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ChatHistory':
        """Create a ChatHistory instance from a JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def save_to_file(self, filepath: str) -> None:
        """Save the chat history to a file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json(indent=2))
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'ChatHistory':
        """Load chat history from a file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            json_str = f.read()
        return cls.from_json(json_str)
