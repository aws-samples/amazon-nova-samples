"""Session controller — conversation lifecycle coordinator.

Wires together BedrockConnection, ResponseParser, ConversationState,
ToolRegistry, EventTemplates, and StreamCallback.  All business logic
decisions (agent switching, barge-in handling, tool execution, history
updates) live here.
"""
import asyncio
import base64
import json
import logging
import uuid
from typing import Optional, Set

from src.connection.bedrock_connection import BedrockConnection
from src.session.conversation_state import ConversationState
from src.agents.tool_registry import ToolRegistry
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
)
from src.session.callbacks import StreamCallback
from src.connection.response_parser import ResponseParser
from src.connection.event_templates import EventTemplates
from src.utils import debug_print
from src.agents.agent_config import AGENTS

logger = logging.getLogger("sonic.session")


class SessionController:
    """Central coordinator for a single conversation session.

    Responsibilities:
      - Open the Bedrock connection and send the initialisation sequence
      - Receive raw responses, parse them into typed events, dispatch business logic
      - Execute tools asynchronously and send results back
      - Notify the AudioStreamer (via StreamCallback) of audio output, barge-in, and switch events
      - Manage session teardown
    """

    def __init__(
        self,
        connection: BedrockConnection,
        state: ConversationState,
        registry: ToolRegistry,
        callback: StreamCallback,
        voice_id: str,
        system_prompt: str,
    ) -> None:
        self._connection = connection
        self._state = state
        self._registry = registry
        self._callback = callback
        self._voice_id = voice_id
        self._system_prompt = system_prompt

        # Session IDs
        self._prompt_name = str(uuid.uuid4())
        self._content_name = str(uuid.uuid4())
        self._audio_content_name = str(uuid.uuid4())

        # Response tracking
        self._display_assistant_text = False
        self._role: Optional[str] = None

        # Tool handling
        self._pending_tool_tasks: dict[str, asyncio.Task] = {}
        self._tool_name = ""
        self._tool_use_id = ""
        self._tool_use_content: dict = {}

        # Background tasks
        self._response_task: Optional[asyncio.Task] = None
        self._is_active = False
        self._audio_send_count = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_session(self) -> None:
        """Open connection, send init events, start response processing."""
        debug_print("Opening connection")
        await self._connection.open()
        self._is_active = True

        debug_print("Sending initialization events")
        await self._send_initialization_events()
        debug_print("Initialization events sent")

        self._response_task = asyncio.create_task(self._process_responses())
        await asyncio.sleep(0.1)
        logger.info("Session started (voice=%s)", self._voice_id)

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Encode raw audio bytes as base64 and send to Bedrock."""
        self._audio_send_count += 1
        if self._audio_send_count % 50 == 1:
            debug_print(f"Audio chunk #{self._audio_send_count} ({len(audio_bytes)} bytes)")
        blob = base64.b64encode(audio_bytes).decode("utf-8")
        event = EventTemplates.audio_input(
            self._prompt_name, self._audio_content_name, blob
        )
        await self._connection.send(event)

    async def send_audio_content_start_event(self) -> None:
        """Send audio content start event."""
        event = EventTemplates.content_start(
            self._prompt_name, self._audio_content_name
        )
        await self._connection.send(event)

    async def send_audio_content_end_event(self) -> None:
        """Send audio content end event."""
        if self._is_active:
            event = EventTemplates.content_end(
                self._prompt_name, self._audio_content_name
            )
            await self._connection.send(event)
            debug_print("Audio ended")

    async def stop(self) -> None:
        """Close connection and cancel pending tasks."""
        if not self._is_active:
            return

        debug_print("Stopping session")
        logger.info("Stopping session (pending_tools=%d)", len(self._pending_tool_tasks))
        self._is_active = False

        # Cancel pending tool tasks
        for task in self._pending_tool_tasks.values():
            task.cancel()
        self._pending_tool_tasks.clear()

        # Cancel response processing
        if self._response_task and not self._response_task.done():
            self._response_task.cancel()

        # Send close sequence
        try:
            await self.send_audio_content_end_event()
            await self._connection.send(
                EventTemplates.prompt_end(self._prompt_name)
            )
            await self._connection.send(EventTemplates.session_end())
        except Exception as e:
            debug_print(f"Error during stop: {e}")

        await self._connection.close()
        logger.info("Session stopped")
        debug_print("Session stopped")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def prompt_name(self) -> str:
        return self._prompt_name

    @property
    def audio_content_name(self) -> str:
        return self._audio_content_name

    # ------------------------------------------------------------------
    # Initialisation sequence
    # ------------------------------------------------------------------

    async def _send_initialization_events(self) -> None:
        """Send the startup sequence: session start, prompt start, system prompt, history, greeting."""
        system_prompt = self._system_prompt or "You are a friend engaging in natural real-time conversation."

        tool_schemas = self._registry.get_schemas_for_agent(
            self._state.active_agent, AGENTS
        )

        events = [
            EventTemplates.start_session(),
            EventTemplates.prompt_start(
                self._prompt_name, self._voice_id, tool_schemas
            ),
            EventTemplates.text_content_start(
                self._prompt_name, self._content_name, "SYSTEM"
            ),
            EventTemplates.text_input(
                self._prompt_name, self._content_name, system_prompt
            ),
            EventTemplates.content_end(self._prompt_name, self._content_name),
        ]

        for event in events:
            await self._connection.send(event)
            await asyncio.sleep(0.1)

        # Send conversation history
        history = self._state.get_history()
        if history:
            print(f"📝 Add conversation history: {len(history)} messages")
            debug_print(f"Sending history: {len(history)} messages")
            # Drop last message and leading assistant messages (matches original behaviour)
            history = history[:-1]
            while history and history[0].get("role") == "ASSISTANT":
                history.pop(0)
            for msg in history:
                await self._send_history_message(msg)

        # Send greeting prompt
        speak_first_content_name = str(uuid.uuid4())
        greeting_events = [
            EventTemplates.text_content_start(
                self._prompt_name,
                content_name=speak_first_content_name,
                role="USER",
                interactive=True,
            ),
            EventTemplates.text_input(
                self._prompt_name,
                speak_first_content_name,
                "Greet the user with his name and SHORT explanation your role",
            ),
            EventTemplates.content_end(
                self._prompt_name, speak_first_content_name
            ),
        ]
        for event in greeting_events:
            await self._connection.send(event)
            await asyncio.sleep(0.1)

    async def _send_history_message(self, message: dict) -> None:
        """Send a single history message to Bedrock."""
        history_content_name = str(uuid.uuid4())
        events = [
            EventTemplates.text_content_start(
                self._prompt_name, history_content_name, message["role"]
            ),
            EventTemplates.text_input(
                self._prompt_name, history_content_name, message["content"]
            ),
            EventTemplates.content_end(self._prompt_name, history_content_name),
        ]
        for event in events:
            await self._connection.send(event)
            await asyncio.sleep(0.1)

    # ------------------------------------------------------------------
    # Response processing loop
    # ------------------------------------------------------------------

    async def _process_responses(self) -> None:
        """Main response loop: receive → parse → dispatch."""
        debug_print("Response processing loop started")
        try:
            async for raw_data in self._connection.receive():
                if not self._is_active or self._state.switch_requested:
                    break
                event = ResponseParser.parse(raw_data)
                debug_print(f"Event: {type(event).__name__}")
                await self._dispatch_event(event)
        except asyncio.CancelledError:
            debug_print("Response processing cancelled")
        except Exception as e:
            logger.error("Response processing error: %s", e, exc_info=True)
        finally:
            self._is_active = False

    # ------------------------------------------------------------------
    # Event dispatch — all business logic lives here
    # ------------------------------------------------------------------

    async def _dispatch_event(self, event: StreamEvent) -> None:
        """Route typed events to the appropriate business logic handler."""

        if isinstance(event, CompletionStartEvent):
            debug_print(f"Completion start: {event.data}")

        elif isinstance(event, ContentStartEvent):
            self._handle_content_start(event)

        elif isinstance(event, TextOutputEvent):
            self._handle_text_output(event)

        elif isinstance(event, AudioOutputEvent):
            self._handle_audio_output(event)

        elif isinstance(event, BargeInEvent):
            self._handle_barge_in()

        elif isinstance(event, ToolUseEvent):
            await self._handle_tool_use(event)

        elif isinstance(event, ContentEndEvent):
            self._handle_content_end(event)

        elif isinstance(event, CompletionEndEvent):
            debug_print("Completion end")

        elif isinstance(event, UsageEvent):
            debug_print(f"Usage: {event.data}")

    # ------------------------------------------------------------------
    # Business logic handlers
    # ------------------------------------------------------------------

    def _handle_content_start(self, event: ContentStartEvent) -> None:
        """Track role and whether this is a final (displayable) response."""
        debug_print("Content start")
        self._role = event.role
        if event.is_final_response:
            self._display_assistant_text = True
        else:
            self._display_assistant_text = False

    def _handle_text_output(self, event: TextOutputEvent) -> None:
        """Append to conversation state and/or print to console."""
        role = event.role
        content = event.content

        if (self._role == "ASSISTANT" and self._display_assistant_text) or self._role == "USER":
            self._state.append_message(role, content)
        if (self._role == "ASSISTANT" and not self._display_assistant_text) or self._role == "USER":
            print(f"{role.title()}: {content}")

    def _handle_audio_output(self, event: AudioOutputEvent) -> None:
        """Decode base64 audio and push to callback."""
        audio_bytes = base64.b64decode(event.audio_base64)
        debug_print(f"Audio output: {len(audio_bytes)} bytes")
        self._callback.on_audio_output(audio_bytes)

    def _handle_barge_in(self) -> None:
        """Notify callback of barge-in."""
        debug_print("Barge-in detected")
        self._callback.on_barge_in()

    async def _handle_tool_use(self, event: ToolUseEvent) -> None:
        """Handle tool use — either agent switch or regular tool execution."""
        self._tool_name = event.tool_name
        self._tool_use_id = event.tool_use_id
        self._tool_use_content = {
            "toolName": event.tool_name,
            "toolUseId": event.tool_use_id,
            "content": event.content,
        }

        if event.tool_name == "switch_agent":
            target = event.content.get("role", "support").lower()
            logger.info("Agent switch requested → %s", target)
            self._state.request_switch(target)
            await asyncio.sleep(0.1)
            self._callback.on_switch_requested()
            print(f"🎯 Switching to: {target}")
        else:
            logger.info("Tool invoked: %s (id=%s)", event.tool_name, event.tool_use_id)
            print(f"🎯 Tool use: {event.tool_name}")
            debug_print(f"Tool: {event.tool_name}, ID: {event.tool_use_id}")

    def _handle_content_end(self, event: ContentEndEvent) -> None:
        """On TOOL content end, kick off async tool execution."""
        if event.content_type == "TOOL":
            debug_print("Processing tool")
            self._execute_tool_async(
                self._tool_name, self._tool_use_content, self._tool_use_id
            )
        else:
            debug_print("Content end")

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def _execute_tool_async(
        self, tool_name: str, tool_content: dict, tool_use_id: str
    ) -> None:
        """Fire-and-forget async tool execution with result sent back to Bedrock."""
        content_name = str(uuid.uuid4())
        task = asyncio.create_task(
            self._execute_tool_and_send_result(
                tool_name, tool_content, tool_use_id, content_name
            )
        )
        self._pending_tool_tasks[content_name] = task
        task.add_done_callback(
            lambda t: self._handle_tool_completion(t, content_name)
        )

    def _handle_tool_completion(self, task: asyncio.Task, content_name: str) -> None:
        """Clean up after a tool task finishes."""
        self._pending_tool_tasks.pop(content_name, None)
        if task.done() and not task.cancelled():
            exc = task.exception()
            if exc:
                debug_print(f"Tool task failed: {exc}")

    async def _execute_tool_and_send_result(
        self,
        tool_name: str,
        tool_content: dict,
        tool_use_id: str,
        content_name: str,
    ) -> None:
        """Execute a tool via ToolRegistry and send the result back to Bedrock."""
        try:
            debug_print(f"Executing tool: {tool_name}")
            result = await self._registry.execute(tool_name, tool_content)

            await self._connection.send(
                EventTemplates.tool_content_start(
                    self._prompt_name, content_name, tool_use_id
                )
            )
            await self._connection.send(
                EventTemplates.tool_result(
                    self._prompt_name, content_name, result
                )
            )
            await self._connection.send(
                EventTemplates.content_end(self._prompt_name, content_name)
            )
            debug_print(f"Tool complete: {tool_name}")
        except Exception as e:
            debug_print(f"Tool error: {e}")
            try:
                error_result = {"error": f"Tool failed: {e}"}
                await self._connection.send(
                    EventTemplates.tool_content_start(
                        self._prompt_name, content_name, tool_use_id
                    )
                )
                await self._connection.send(
                    EventTemplates.tool_result(
                        self._prompt_name, content_name, error_result
                    )
                )
                await self._connection.send(
                    EventTemplates.content_end(self._prompt_name, content_name)
                )
            except Exception as send_error:
                debug_print(f"Failed to send error: {send_error}")
