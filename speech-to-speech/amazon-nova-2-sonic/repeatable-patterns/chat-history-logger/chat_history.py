import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

class ChatMessage:
    """Base class for all chat history entries"""
    
    def __init__(self, role: str, timestamp: Optional[float] = None):
        self.role = role
        self.timestamp = timestamp or datetime.now().timestamp()
    
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
    """Manages the conversation history including messages and tool interactions"""
    
    def __init__(self):
        # All messages in chronological order
        self.messages: List[ChatMessage] = []
    
    def add_message(self, role: str, content: str) -> TextMessage:
        """Add a new text message to the chat history"""
        message = TextMessage(role, content)
        self.messages.append(message)
        return message
    
    def add_tool_call(
        self, 
        tool_use_content: Any
    ) -> ToolCallMessage:
        """Add a tool call to the chat history"""
        message = ToolCallMessage(tool_use_content)
        self.messages.append(message)
        return message
    
    def add_tool_result(
        self, 
        tool_use_id: str, 
        result: Any
    ) -> ToolResultMessage:
        """Add a tool result to the chat history"""
        message = ToolResultMessage(tool_use_id, result)
        self.messages.append(message)
        return message
    
    def get_full_history(self) -> str:
        """Get the full conversation history as a formatted string"""
        history_lines = []
        for msg in self.messages:
            history_lines.append(str(msg))
        
        return "\n".join(history_lines)
    
    def get_last_n_messages(self, n: int) -> List[ChatMessage]:
        """Get the last n messages in the chat history"""
        return self.messages[-n:] if n < len(self.messages) else self.messages.copy()
    
    def get_messages_by_role(self, role: str) -> List[ChatMessage]:
        """Get all messages with the specified role"""
        return [msg for msg in self.messages if msg.role == role]
    
    def get_tool_calls(self) -> List[ToolCallMessage]:
        """Get all tool call messages"""
        return [msg for msg in self.messages if isinstance(msg, ToolCallMessage)]
    
    def get_tool_results(self) -> List[ToolResultMessage]:
        """Get all tool result messages"""
        return [msg for msg in self.messages if isinstance(msg, ToolResultMessage)]
    
    def clear(self) -> None:
        """Clear the chat history"""
        self.messages.clear()
    
    def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """Convert the chat history to a dictionary"""
        return {
            "messages": [msg.to_dict() for msg in self.messages]
        }
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """Convert the chat history to a JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, List[Dict[str, Any]]]) -> 'ChatHistory':
        """Create a ChatHistory instance from a dictionary"""
        history = cls()
        
        for msg_data in data.get("messages", []):
            msg_type = msg_data.get("type", "")
            
            if msg_type == "text":
                history.add_text_message(
                    msg_data.get("role", ""),
                    msg_data.get("content", "")
                )
            elif msg_type == "tool_call":
                history.add_tool_call(
                    msg_data.get("tool_name", ""),
                    msg_data.get("tool_use_id", ""),
                    msg_data.get("input", {})
                )
            elif msg_type == "tool_result":
                history.add_tool_result(
                    msg_data.get("tool_name", ""),
                    msg_data.get("tool_use_id", ""),
                    msg_data.get("result", {})
                )
                
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