"""Property-based tests for ConversationState.

**Validates: Requirements 1.3, 1.4, 1.5**
"""

import sys
import os

from hypothesis import given, settings
from hypothesis import strategies as st

from src.session.conversation_state import ConversationState


# Feature: architecture-refactor, Property 1: Agent switch request is recorded atomically
@given(agent_name=st.text(min_size=1))
@settings(max_examples=200)
def test_request_switch_records_atomically(agent_name: str):
    """For any valid agent name string, calling request_switch(agent_name) on a
    ConversationState SHALL result in switch_requested being True and
    switch_target being equal to the provided agent name.

    **Validates: Requirements 1.3**
    """
    state = ConversationState()
    state.request_switch(agent_name)

    assert state.switch_requested is True
    assert state.switch_target == agent_name


# Feature: architecture-refactor, Property 2: Conversation history preserves all appended messages in order
@given(
    messages=st.lists(
        st.tuples(
            st.text(min_size=1),
            st.text(min_size=1),
        ),
        min_size=0,
        max_size=50,
    )
)
@settings(max_examples=200)
def test_history_preserves_appended_messages_in_order(messages):
    """For any sequence of (role, content) string pairs appended to a
    ConversationState, calling get_history() SHALL return a list of the same
    length containing dictionaries with matching role and content values in the
    same order they were appended.

    **Validates: Requirements 1.4, 1.5**
    """
    state = ConversationState()

    for role, content in messages:
        state.append_message(role, content)

    history = state.get_history()

    assert len(history) == len(messages)
    for (expected_role, expected_content), entry in zip(messages, history):
        assert entry["role"] == expected_role
        assert entry["content"] == expected_content
