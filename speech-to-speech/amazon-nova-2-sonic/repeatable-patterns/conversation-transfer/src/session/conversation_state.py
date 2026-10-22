"""Conversation state management."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ConversationState:
    """Owns conversation history, active agent, and switch state."""

    active_agent: str = "support"
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    switch_requested: bool = False
    switch_target: Optional[str] = None

    def append_message(self, role: str, content: str) -> None:
        """Append a message preserving role and content."""
        self.conversation_history.append({"role": role, "content": content})

    def request_switch(self, target_agent: str) -> None:
        """Record an agent switch request atomically."""
        self.switch_target = target_agent
        self.switch_requested = True

    def complete_switch(self) -> str:
        """Complete the pending switch, returning the new agent name."""
        agent = self.switch_target
        self.active_agent = agent
        self.switch_requested = False
        self.switch_target = None
        return agent

    def get_history(self) -> List[Dict[str, str]]:
        """Return a copy of the conversation history."""
        return list(self.conversation_history)

    def reset_switch(self) -> None:
        """Clear any pending switch request."""
        self.switch_requested = False
        self.switch_target = None
