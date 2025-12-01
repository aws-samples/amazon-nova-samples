import os
import asyncio
import time
import json
import uuid
import wave
import datetime
from collections import deque
from typing import Optional, Deque
from enum import Enum

class SessionState(Enum):
    """Enumeration of possible session states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    CLOSING = "closing"
    CLOSED = "closed"

class SessionInfo:
    """Information about a streaming session"""
    def __init__(self, session_id: str, stream_manager, start_time: float):
        self.session_id = session_id
        self.stream_manager = stream_manager
        self.start_time = start_time
        self.state = SessionState.INITIALIZING
        self.received_completion_start = False
        self.barge_in_detected = False
        self.input_audio_recorder = None
        self.output_audio_recorder = None
        # Track current content generation stage
        self.current_generation_stage = None
        self.current_content_role = None
        self.current_content_type = None  # Track if it's TEXT or AUDIO
        # Track model's session ID
        self.model_session_id = None
        # Track initialization audio (buffer + real-time sent to this session)
        self.initialization_audio_recorder = None
        self.recording_initialization_audio = False
        # Track if audio contentStart has been sent
        self.audio_content_started = False
        # Track when we last received output from this session (for timeout detection)
        self.last_output_time = time.time()
        # Track if we've received FINAL text (indicates assistant finished generating)
        self.received_final_text = False
        # Track speculative and final text counts for matching
        self.speculative_text_count = 0
        self.final_text_count = 0
        # # Track if we've received audio contentEnd with END_TURN or INTERRUPTED
        # self.received_audio_end_turn = False
        # self.audio_stop_reason = None

    def get_duration(self) -> float:
        """Get the duration of the session in seconds"""
        return time.time() - self.start_time

    def should_transition(self, threshold: float) -> bool:
        """Check if session should transition based on duration"""
        return self.get_duration() >= threshold

class AudioBuffer:
    """Buffer for storing audio chunks during transition"""
    def __init__(self, max_duration_seconds: float, sample_rate: int = 16000, sample_width: int = 2):
        self.max_duration_seconds = max_duration_seconds
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        # Calculate max buffer size in bytes
        self.max_buffer_size = int(max_duration_seconds * sample_rate * sample_width)
        self.buffer: Deque[bytes] = deque()
        self.total_size = 0

    def add_chunk(self, audio_chunk: bytes):
        """Add an audio chunk to the buffer"""
        self.buffer.append(audio_chunk)
        self.total_size += len(audio_chunk)

        # Remove old chunks if buffer exceeds max size
        while self.total_size > self.max_buffer_size and self.buffer:
            removed = self.buffer.popleft()
            self.total_size -= len(removed)

    def get_all_chunks(self) -> list:
        """Get all buffered audio chunks"""
        return list(self.buffer)

    def clear(self):
        """Clear the buffer"""
        self.buffer.clear()
        self.total_size = 0

    def is_empty(self) -> bool:
        """Check if buffer is empty"""
        return len(self.buffer) == 0

class AudioRecorder:
    """Records audio streams to WAV files"""
    def __init__(self, file_path: str, sample_rate: int, sample_width: int = 2, channels: int = 1):
        self.file_path = file_path
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.channels = channels
        self.wav_file = None
        self.is_recording = False

    def start_recording(self):
        """Start recording audio"""
        if self.is_recording:
            return

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        self.wav_file = wave.open(self.file_path, 'wb')
        self.wav_file.setnchannels(self.channels)
        self.wav_file.setsampwidth(self.sample_width)
        self.wav_file.setframerate(self.sample_rate)
        self.is_recording = True

    def write_chunk(self, audio_chunk: bytes):
        """Write an audio chunk to the file"""
        if self.is_recording and self.wav_file:
            self.wav_file.writeframes(audio_chunk)

    def stop_recording(self):
        """Stop recording and close the file"""
        if not self.is_recording:
            return

        self.is_recording = False
        if self.wav_file:
            self.wav_file.close()
            self.wav_file = None

        # Rename to final path if it was set (deferred rename to avoid audio loss)
        if hasattr(self, 'final_path') and self.final_path:
            if os.path.exists(self.file_path):
                try:
                    os.rename(self.file_path, self.final_path)
                    self.file_path = self.final_path
                    print(f"[RECORDER] Successfully renamed to {os.path.basename(self.file_path)}")
                except Exception as e:
                    print(f"[RECORDER] Error renaming {self.file_path} to {self.final_path}: {e}")
            else:
                print(f"[RECORDER] Cannot rename - source file doesn't exist: {self.file_path}")

class ConversationHistory:
    """Manages conversation history for session transitions"""
    def __init__(self, max_single_message_bytes: int = 1024, max_chat_history_bytes: int = 40960):
        self.messages = []
        self.max_single_message_bytes = max_single_message_bytes
        self.max_chat_history_bytes = max_chat_history_bytes

    def add_message(self, role: str, content: str, message_type: str = "text") -> dict:
        """Add a message to the history with byte limit enforcement

        Returns:
            dict with keys:
            - 'truncated': bool - whether message was truncated
            - 'messages_removed': int - number of old messages removed
            - 'total_bytes': int - total history size in bytes
        """
        was_truncated = False

        # Truncate message content if it exceeds single message limit
        content_bytes = content.encode('utf-8')
        if len(content_bytes) > self.max_single_message_bytes:
            was_truncated = True
            # Truncate to fit within limit, leaving room for truncation marker
            truncation_marker = "... [truncated]"
            max_content_bytes = self.max_single_message_bytes - len(truncation_marker.encode('utf-8'))
            # Decode safely, handling potential mid-character truncation
            truncated_content = content_bytes[:max_content_bytes].decode('utf-8', errors='ignore')
            content = truncated_content + truncation_marker

        messages_before = len(self.messages)

        self.messages.append({
            "role": role,
            "content": content,
            "type": message_type,
            "timestamp": time.time()
        })

        # Trim history to stay within total byte limit
        self._trim_history()

        messages_removed = messages_before - len(self.messages) + 1

        return {
            'truncated': was_truncated,
            'messages_removed': messages_removed if messages_removed > 1 else 0,
            'total_bytes': self._get_total_size_bytes()
        }

    def _get_message_size_bytes(self, message: dict) -> int:
        """Calculate the byte size of a message"""
        # Size includes role + content + metadata
        return len(message["content"].encode('utf-8')) + len(message["role"].encode('utf-8'))

    def _get_total_size_bytes(self) -> int:
        """Calculate total byte size of all messages"""
        return sum(self._get_message_size_bytes(msg) for msg in self.messages)

    def _trim_history(self):
        """Trim history to stay within configured byte limits"""
        # Remove oldest messages until we're under the total byte limit
        while self.messages and self._get_total_size_bytes() > self.max_chat_history_bytes:
            self.messages.pop(0)  # Remove oldest message

    def get_history_events(self, prompt_name: str) -> list:
        """Get conversation history as Bedrock events, splitting large messages if needed"""
        events = []

        for message in self.messages:
            role = message["role"].upper()
            content = message["content"]
            content_bytes = content.encode('utf-8')

            # If content is larger than max_single_message_bytes, split it
            if len(content_bytes) > self.max_single_message_bytes:
                # Split into chunks
                chunks = []
                while len(content_bytes) > 0:
                    chunk = content_bytes[:self.max_single_message_bytes]
                    chunks.append(chunk.decode('utf-8', errors='ignore'))
                    content_bytes = content_bytes[self.max_single_message_bytes:]

                # Send each chunk as a separate content block
                for chunk in chunks:
                    content_name = str(uuid.uuid4())

                    # Content start event
                    content_start = {
                        "event": {
                            "contentStart": {
                                "promptName": prompt_name,
                                "contentName": content_name,
                                "type": "TEXT",
                                "role": role,
                                "interactive": False,
                                "textInputConfiguration": {
                                    "mediaType": "text/plain"
                                }
                            }
                        }
                    }
                    events.append(json.dumps(content_start))

                    # Text input event
                    text_input = {
                        "event": {
                            "textInput": {
                                "promptName": prompt_name,
                                "contentName": content_name,
                                "content": chunk
                            }
                        }
                    }
                    events.append(json.dumps(text_input))

                    # Content end event
                    content_end = {
                        "event": {
                            "contentEnd": {
                                "promptName": prompt_name,
                                "contentName": content_name
                            }
                        }
                    }
                    events.append(json.dumps(content_end))
            else:
                # Normal case: single content block
                content_name = str(uuid.uuid4())

                # Content start event
                content_start = {
                    "event": {
                        "contentStart": {
                            "promptName": prompt_name,
                            "contentName": content_name,
                            "type": "TEXT",
                            "role": role,
                            "interactive": False,
                            "textInputConfiguration": {
                                "mediaType": "text/plain"
                            }
                        }
                    }
                }
                events.append(json.dumps(content_start))

                # Text input event
                text_input = {
                    "event": {
                        "textInput": {
                            "promptName": prompt_name,
                            "contentName": content_name,
                            "content": content
                        }
                    }
                }
                events.append(json.dumps(text_input))

                # Content end event
                content_end = {
                    "event": {
                        "contentEnd": {
                            "promptName": prompt_name,
                            "contentName": content_name
                        }
                    }
                }
                events.append(json.dumps(content_end))

        return events

    def clear(self):
        """Clear the conversation history"""
        self.messages.clear()

class SessionTransitionManager:
    """Manages session transitions for long-running conversations"""

    def __init__(self, config_path: str = "./session_config.json"):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.transition_config = self.config["session_transition"]
        self.logging_config = self.config["session_logging"]

        # Session management
        self.current_session: Optional[SessionInfo] = None
        self.next_session: Optional[SessionInfo] = None
        self.session_counter = 0

        # Audio buffering for transitions
        self.audio_buffer = AudioBuffer(
            max_duration_seconds=self.transition_config["audio_buffer_duration_seconds"]
        )
        self.is_buffering = False

        # Conversation history with byte limits
        self.conversation_history = ConversationHistory(
            max_single_message_bytes=self.transition_config.get("max_single_message_bytes", 1024),
            max_chat_history_bytes=self.transition_config.get("max_chat_history_bytes", 40960)
        )

        # Transition state
        self.is_transitioning = False
        self.transition_ready = False
        self.waiting_for_audio_start = False
        self.waiting_for_completion = False
        self.user_was_speaking = False
        self.barge_in_occurred = False
        self.audio_start_wait_start = None
        self.audio_start_timeout = self.transition_config.get("audio_start_timeout_seconds", 5.0)
        self.audio_chunk_count = 0  # For debugging audio routing

        # Recording directory with timestamp for this conversation
        if self.transition_config["enable_session_recording"]:
            base_recording_dir = self.transition_config["recording_output_dir"]
            # Create a unique directory for this conversation
            conversation_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.recording_dir = os.path.join(base_recording_dir, f"conversation_{conversation_timestamp}")
            os.makedirs(self.recording_dir, exist_ok=True)
            self._log(f"Recording directory: {self.recording_dir}")
        else:
            self.recording_dir = None

        # Lock for thread-safe operations
        self.lock = asyncio.Lock()

        # Event monitoring task
        self.monitor_task = None

        # Next session ready timeout monitoring
        self.next_session_created_time = None
        self.next_session_ready_timeout = self.transition_config.get("next_session_ready_timeout_seconds", 30)
        self.next_session_monitor_task = None

    def _log(self, message: str, log_type: str = "transition"):
        """Log a message if logging is enabled"""
        if log_type == "transition" and self.logging_config["log_transitions"]:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[SESSION_MANAGER {timestamp}] {message}")
        elif log_type == "barge_in" and self.logging_config["log_barge_in_events"]:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[BARGE_IN {timestamp}] {message}")
        elif log_type == "audio" and self.logging_config["log_audio_events"]:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[AUDIO {timestamp}] {message}")

    async def create_session(self, stream_manager_class, **kwargs) -> SessionInfo:
        """Create a new session"""
        session_id = f"session_{self.session_counter}"
        self.session_counter += 1

        self._log(f"Creating {session_id}")

        # Create stream manager with session_id
        kwargs['session_id'] = session_id
        stream_manager = stream_manager_class(**kwargs)

        # Initialize the stream
        await stream_manager.initialize_stream()

        # Create session info
        session_info = SessionInfo(
            session_id=session_id,
            stream_manager=stream_manager,
            start_time=time.time()
        )

        # Set up audio recording if enabled
        if self.transition_config["enable_session_recording"] and self.recording_dir:
            # Will update filename once we get model_session_id from completionStart
            # For now, use temporary files
            input_file = os.path.join(
                self.recording_dir,
                f"{session_id}_input_temp.wav"
            )
            output_file = os.path.join(
                self.recording_dir,
                f"{session_id}_output_temp.wav"
            )
        
            session_info.input_audio_recorder = AudioRecorder(
                input_file, sample_rate=16000, sample_width=2
            )
            session_info.output_audio_recorder = AudioRecorder(
                output_file, sample_rate=24000, sample_width=2
            )

            session_info.input_audio_recorder.start_recording()
            session_info.output_audio_recorder.start_recording()

        session_info.state = SessionState.ACTIVE
        self._log(f"{session_id} created and active")

        return session_info

    async def initialize_first_session(self, stream_manager_class, **kwargs):
        """Initialize the first session"""
        self.current_session = await self.create_session(stream_manager_class, **kwargs)

        # Start monitoring events
        self.monitor_task = asyncio.create_task(self._monitor_events())

    async def _monitor_events(self):
        """Monitor events from the current session to detect transition opportunities"""
        while True:
            try:
                if not self.current_session or self.current_session.state == SessionState.CLOSED:
                    await asyncio.sleep(0.1)
                    continue

                threshold = self.transition_config["transition_threshold_seconds"]
                if (self.current_session.should_transition(threshold) and
                    not self.is_transitioning and
                    not self.waiting_for_audio_start):

                    self._log(f"Session duration {self.current_session.get_duration():.1f}s reached threshold {threshold}s")
                    self.waiting_for_audio_start = True
                    self.audio_start_wait_start = time.time()
                    self._log("Waiting for AUDIO contentStart (assistant starts speaking)...")

                if (self.waiting_for_audio_start and
                    self.audio_start_wait_start and
                    (time.time() - self.audio_start_wait_start) > self.audio_start_timeout):
                    self._log(f"TIMEOUT: No AUDIO contentStart after {self.audio_start_timeout}s, forcing transition")
                    self.is_buffering = True
                    await self._initiate_transition()

                stream_manager = self.current_session.stream_manager
                if not stream_manager.output_queue.empty():
                    try:
                        event = await asyncio.wait_for(
                            stream_manager.output_queue.get(),
                            timeout=0.01
                        )

                        await self._process_event(event, self.current_session)

                    except asyncio.TimeoutError:
                        pass

                await asyncio.sleep(0.01)

            except Exception as e:
                self._log(f"Error in event monitor: {e}")
                await asyncio.sleep(0.1)

    async def _process_event(self, event: dict, session: SessionInfo):
        """Process an event from a session"""
        if 'event' not in event:
            return

        # Skip processing if the session's stream was force-stopped
        if session.stream_manager and not session.stream_manager.is_active:
            return

        event_data = event['event']

        # Track contentStart to know the generation stage for subsequent text
        if 'contentStart' in event_data:
            content_start = event_data['contentStart']
            session.current_content_role = content_start.get('role')
            session.current_content_type = content_start.get('type')

            if 'additionalModelFields' in content_start:
                try:
                    additional_fields = json.loads(content_start['additionalModelFields'])
                    session.current_generation_stage = additional_fields.get('generationStage')
                except json.JSONDecodeError:
                    session.current_generation_stage = None
            else:
                session.current_generation_stage = None

            if (session == self.current_session and
                self.waiting_for_audio_start and
                session.current_content_type == 'AUDIO' and
                session.current_content_role == 'ASSISTANT'):
                self._log(f"[AUDIO_START] AUDIO contentStart detected in {session.session_id} - starting buffer and initiating transition")
                self.is_buffering = True
                await self._initiate_transition()

            if (session.current_content_role == 'USER' and
                session == self.current_session and
                self.is_transitioning and
                self.next_session and
                self.next_session.received_completion_start):
                self._log(f"User contentStart detected during monitoring - treating as barge-in")
                session.barge_in_detected = True
                self.barge_in_occurred = True

        elif 'completionStart' in event_data:
            completion_start = event_data['completionStart']
            model_session_id = completion_start.get('sessionId')

            if model_session_id and not session.model_session_id:
                session.model_session_id = model_session_id
                self._log(f"[COMPLETION_START] {session.session_id} | Bedrock sessionId: {model_session_id}")

                if self.recording_dir:
                    await self._rename_session_recordings(session)

        # Handle text output
        elif 'textOutput' in event_data:
            text_content = event_data['textOutput'].get('content', '')
            role = event_data['textOutput'].get('role', '')

            # Detect barge-in
            if '{ "interrupted" : true }' in text_content:
                session.barge_in_detected = True
                self._log(f"Barge-in detected in {session.session_id}", log_type="barge_in")

                # Clear audio output queue to stop playing interrupted audio
                while not session.stream_manager.audio_output_queue.empty():
                    try:
                        session.stream_manager.audio_output_queue.get_nowait()
                    except:
                        break
                self._log(f"Cleared audio queue for {session.session_id}", log_type="barge_in")

                # Track barge-in during transition for buffered audio handling
                if session == self.current_session and self.is_transitioning:
                    self.barge_in_occurred = True
                    self._log("Barge-in during transition - will send buffered audio to next session", log_type="barge_in")

            # Track USER speech during transition - treat as barge-in
            elif role == 'USER' and text_content and self.is_transitioning and session == self.current_session:
                self.user_was_speaking = True
                # When user speaks during transition, mark as barge-in
                # This means buffered audio (including this user speech) will be sent to next session
                if not self.barge_in_occurred:
                    self.barge_in_occurred = True
                    self._log("User spoke during transition - treating as barge-in (will send buffered audio to next session)", log_type="barge_in")

                # If this is a FORCED transition (no assistant response yet), complete transition immediately
                # Don't wait for text pairs to match since there won't be any assistant response
                if session.final_text_count == 0 and self.waiting_for_completion:
                    self._log("User spoke during FORCED transition (no assistant response yet) - completing transition immediately", log_type="barge_in")
                    asyncio.create_task(self._send_history_and_start_audio())

            # Track conversation for history
            # During transition monitoring period, ONLY accept USER text from next_session
            # (both sessions receive audio, but next_session will carry conversation forward)
            # Before transition, only accept from current_session
            if self.is_transitioning and role == 'USER':
                # During transition: only next_session's USER text
                is_relevant_session = (session == self.next_session)
            else:
                # Normal operation or ASSISTANT text: use current_session
                is_relevant_session = (session == self.current_session)

            if is_relevant_session and role in ['USER', 'ASSISTANT'] and text_content and '{ "interrupted" : true }' not in text_content:
                if role == 'USER':
                    # Always add USER messages
                    result = self.conversation_history.add_message(role, text_content, "text")
                    self._log(f"[{session.session_id}] Added to history: {role}: {text_content[:50]}...", log_type="audio")

                    # If barge-in was detected before transition, set counts equal when user speaks
                    # (user speaking confirms no more FINAL texts will arrive)
                    if (session == self.current_session and
                        session.barge_in_detected and
                        not self.is_transitioning and
                        session.speculative_text_count > session.final_text_count):
                        self._log(f"[BARGE_IN] User speaking after barge-in - setting final={session.speculative_text_count} (was {session.final_text_count})")
                        session.final_text_count = session.speculative_text_count

                    # Log warnings if message was truncated or history was trimmed
                    if result['truncated']:
                        self._log(f"WARNING: Message truncated to {self.conversation_history.max_single_message_bytes} bytes", log_type="transition")
                    if result['messages_removed'] > 0:
                        self._log(f"WARNING: Removed {result['messages_removed']} old messages to stay under {self.conversation_history.max_chat_history_bytes} byte limit", log_type="transition")

                    # Log total history size
                    if result['total_bytes'] > self.conversation_history.max_chat_history_bytes * 0.8:
                        self._log(f"History size: {result['total_bytes']}/{self.conversation_history.max_chat_history_bytes} bytes ({len(self.conversation_history.messages)} messages)", log_type="transition")

                elif role == 'ASSISTANT':
                    generation_stage = session.current_generation_stage

                    if generation_stage == 'SPECULATIVE':
                        session.speculative_text_count += 1
                        self._log(f"[{session.session_id}] SPECULATIVE text #{session.speculative_text_count}: {text_content[:50]}... (skipping, waiting for FINAL)", log_type="audio")

                    elif generation_stage == 'FINAL':
                        session.final_text_count += 1
                        self._log(f"[{session.session_id}] FINAL text #{session.final_text_count}: {text_content[:50]}...", log_type="audio")

                        result = self.conversation_history.add_message(role, text_content, "text")
                        self._log(f"[{session.session_id}] Added FINAL to history", log_type="audio")

                        session.received_final_text = True

                        if (session == self.current_session and
                            self.waiting_for_completion and
                            session.speculative_text_count > 0 and
                            session.final_text_count > 0 and
                            session.speculative_text_count == session.final_text_count):
                            self._log(f"[COMPLETION_SIGNAL] Text pairs matched ({session.speculative_text_count}={session.final_text_count}) - sending history")
                            await self._send_history_and_start_audio()

        elif 'contentEnd' in event_data:
            content_end = event_data['contentEnd']
            content_type = content_end.get('type')
            stop_reason = content_end.get('stopReason')

            if (content_type == 'TEXT' and stop_reason == 'INTERRUPTED' and
                session == self.current_session and
                self.waiting_for_completion):
                self._log(f"[COMPLETION_SIGNAL] TEXT INTERRUPTED received - sending history")
                await self._send_history_and_start_audio()

            if session == self.current_session:
                session.current_generation_stage = None
                session.current_content_role = None

        # Update last output time for ALL events except usageEvent
        # This ensures timeout resets on each meaningful event during monitoring
        if 'usageEvent' not in event_data:
            session.last_output_time = time.time()

    async def _initiate_transition(self):
        """Initiate transition - create next session and wait for completion signal"""
        async with self.lock:
            if self.is_transitioning:
                return

            self.is_transitioning = True
            self.waiting_for_audio_start = False
            self.waiting_for_completion = True
            self.audio_start_wait_start = None

        self._log("=" * 80)
        self._log("TRANSITION INITIATED")
        self._log(f"Current session: {self.current_session.session_id}")
        self._log(f"Session duration: {self.current_session.get_duration():.1f}s")
        self._log(f"Speculative texts so far: {self.current_session.speculative_text_count}")
        self._log(f"Final texts so far: {self.current_session.final_text_count}")
        self._log("=" * 80)

        try:
            buffer_duration_seconds = self.transition_config["audio_buffer_duration_seconds"]
            self.audio_buffer.max_duration_seconds = buffer_duration_seconds
            self.audio_buffer.max_buffer_size = int(buffer_duration_seconds * 16000 * 2)
            current_buffer_duration = self.audio_buffer.total_size / (16000 * 2)
            self._log(f"[BUFFER] Buffering started | Set to {buffer_duration_seconds}s | Currently buffered: {current_buffer_duration:.2f}s ({len(self.audio_buffer.buffer)} chunks)")

            self._log("[NEXT_SESSION] Creating new session...")
            from nova_sonic_tool_use import BedrockStreamManager

            self.next_session = await self.create_session(
                BedrockStreamManager,
                model_id='amazon.nova-2-sonic-v1:0',
                region='us-east-1'
            )
            self._log(f"[NEXT_SESSION] Created: {self.next_session.session_id}")

            # Start monitoring next session readiness
            if self.next_session_monitor_task:
                self.next_session_monitor_task.cancel()
                try:
                    await self.next_session_monitor_task
                except asyncio.CancelledError:
                    pass

            self.next_session_monitor_task = asyncio.create_task(
                self._monitor_next_session_readiness()
            )

            self._log("[WAITING] For completion signal (text pairs match OR TEXT INTERRUPTED)...")
            self._log("[WAITING] Will send history after all FINAL texts received")

            self.transition_ready = True

        except Exception as e:
            self._log(f"[ERROR] Transition failed: {e}")
            self.is_transitioning = False
            self.transition_ready = False
            self.waiting_for_audio_start = False
            self.waiting_for_completion = False
            self.audio_start_wait_start = None

            if self.next_session:
                try:
                    self.next_session.state = SessionState.CLOSING
                    if self.next_session.stream_manager:
                        await self.next_session.stream_manager.close()
                except:
                    pass
                self.next_session = None

            self._log("[RECOVERY] Transition flags reset, will retry on next threshold")
            raise

    async def _monitor_next_session_readiness(self):
        """Monitor if next session receives completionStart within timeout"""
        if not self.next_session:
            return

        session_to_monitor = self.next_session
        start_time = time.time()
        timeout = self.next_session_ready_timeout

        self._log(f"[NEXT_SESSION_MONITOR] Started monitoring {session_to_monitor.session_id} for {timeout}s")

        try:
            while True:
                await asyncio.sleep(1)

                # Check if session received completionStart
                if session_to_monitor.received_completion_start:
                    self._log(f"[NEXT_SESSION_MONITOR] {session_to_monitor.session_id} is ready (received completionStart)")
                    return

                # Check if session is no longer the next session (already promoted or replaced)
                if self.next_session != session_to_monitor:
                    self._log(f"[NEXT_SESSION_MONITOR] {session_to_monitor.session_id} no longer next session, stopping monitor")
                    return

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    self._log(f"[NEXT_SESSION_MONITOR] TIMEOUT after {elapsed:.1f}s - {session_to_monitor.session_id} did not receive completionStart")
                    await self._recreate_next_session(session_to_monitor)
                    return

        except asyncio.CancelledError:
            self._log(f"[NEXT_SESSION_MONITOR] Monitor cancelled for {session_to_monitor.session_id}")
            raise
        except Exception as e:
            self._log(f"[NEXT_SESSION_MONITOR] Error monitoring {session_to_monitor.session_id}: {e}")

    async def _recreate_next_session(self, dead_session: SessionInfo):
        """Close dead next session and create a fresh one"""
        self._log(f"[NEXT_SESSION_RECREATE] Closing dead session {dead_session.session_id}")

        # Close the dead session (promptEnd + sessionEnd only, no audio events)
        try:
            dead_session.state = SessionState.CLOSING
            if dead_session.stream_manager:
                # Response processing error is expected because we never send audio but we have to close session
                await dead_session.stream_manager.send_prompt_end_event()
                await dead_session.stream_manager.send_session_end_event()
                if dead_session.stream_manager.stream_response:
                    try:
                        await asyncio.wait_for(
                            dead_session.stream_manager.stream_response.input_stream.close(),
                            timeout=2.0
                        )
                    except:
                        pass
            dead_session.state = SessionState.CLOSED
            self._log(f"[NEXT_SESSION_RECREATE] Closed dead session {dead_session.session_id}")
        except Exception as e:
            self._log(f"[NEXT_SESSION_RECREATE] Error closing dead session: {e}")

        # Only recreate if we're still transitioning and this is still our next session
        async with self.lock:
            if not self.is_transitioning or self.next_session != dead_session:
                self._log(f"[NEXT_SESSION_RECREATE] Skipping recreation - no longer relevant")
                return

            # Create a fresh next session
            self._log(f"[NEXT_SESSION_RECREATE] Creating fresh replacement session...")
            try:
                from nova_sonic_tool_use import BedrockStreamManager

                self.next_session = await self.create_session(
                    BedrockStreamManager,
                    model_id='amazon.nova-2-sonic-v1:0',
                    region='us-east-1'
                )
                self._log(f"[NEXT_SESSION_RECREATE] Created: {self.next_session.session_id}")

                # Start monitoring the new session
                if self.next_session_monitor_task:
                    self.next_session_monitor_task.cancel()
                    try:
                        await self.next_session_monitor_task
                    except asyncio.CancelledError:
                        pass

                self.next_session_monitor_task = asyncio.create_task(
                    self._monitor_next_session_readiness()
                )

            except Exception as e:
                self._log(f"[NEXT_SESSION_RECREATE] Failed to create replacement session: {e}")
                # Reset transition state on failure
                self.is_transitioning = False
                self.transition_ready = False
                self.waiting_for_completion = False
                self.next_session = None
                raise

    async def _send_history_and_start_audio(self):
        """Send complete history to next session, then start audio"""
        if not self.next_session or not self.waiting_for_completion:
            return

        async with self.lock:
            if not self.waiting_for_completion:
                return
            self.waiting_for_completion = False

        self._log("=" * 80)
        self._log("[HISTORY_SEND] Completion signal received - sending history to next session")
        self._log(f"[HISTORY_SEND] Final text count: {self.current_session.final_text_count}")
        self._log("=" * 80)

        try:
            if self.conversation_history.messages:
                history_size = sum(len(msg.get('content', '')) for msg in self.conversation_history.messages)
                self._log(f"[HISTORY] Sending {len(self.conversation_history.messages)} messages (~{history_size} chars)")

                await self._save_conversation_history(self.next_session)

                history_events = self.conversation_history.get_history_events(
                    self.next_session.stream_manager.prompt_name
                )
                for event in history_events:
                    await self.next_session.stream_manager.send_raw_event(event)
                    await asyncio.sleep(0.01)

                self._log(f"[HISTORY] Sent {len(history_events)} events to {self.next_session.session_id}")
            else:
                self._log("[HISTORY] No history to send")

            self._log("[AUDIO_START] Sending audio contentStart to next session")
            await self.next_session.stream_manager.send_audio_content_start_event()
            self.next_session.audio_content_started = True

            buffer_duration = self.audio_buffer.total_size / (16000 * 2)
            self._log(f"[BUFFER_SEND] Sending {buffer_duration:.2f}s of buffered audio to {self.next_session.session_id}")
            await self._send_buffered_audio_to_next_session()

            self._log("[TRANSITION] Audio sent to next session - closing old session immediately")
            self._log("=" * 80)

            await self._close_old_session_and_promote()

        except Exception as e:
            self._log(f"[ERROR] Failed to send history and start audio: {e}")
            raise

    async def _close_old_session_and_promote(self):
        """Close old session immediately and promote next session"""
        if not self.current_session or not self.next_session:
            return

        old_session = self.current_session

        self._log("=" * 80)
        self._log(f"[PROMOTION] Promoting {self.next_session.session_id} to current session FIRST")
        self._log("=" * 80)

        # PROMOTE FIRST to avoid blocking audio routing
        self.current_session = self.next_session
        self.next_session = None

        self._log(f"[PROMOTION] {self.current_session.session_id} is now the current session")
        self._log(f"[PROMOTION] State: {self.current_session.state}, audio_content_started: {self.current_session.audio_content_started}")

        # Cancel next session monitor (session is now promoted)
        if self.next_session_monitor_task:
            self.next_session_monitor_task.cancel()
            try:
                await self.next_session_monitor_task
            except asyncio.CancelledError:
                pass
            self.next_session_monitor_task = None

        # Reset transition state
        self.is_transitioning = False
        self.transition_ready = False
        self.user_was_speaking = False
        self.barge_in_occurred = False

        self.audio_buffer.clear()
        self.is_buffering = False
        self._log(f"[BUFFER] Cleared and stopped")

        # Now close the old session in the background (don't block)
        self._log("=" * 80)
        self._log(f"[CLOSE_OLD] Closing {old_session.session_id} in background")
        self._log("=" * 80)

        # Mark as closing immediately
        old_session.state = SessionState.CLOSING
        old_session.stream_manager.should_print_text = False
        old_session.stream_manager.is_active = False

        # Clear audio queue
        audio_queue_size = old_session.stream_manager.audio_output_queue.qsize()
        while not old_session.stream_manager.audio_output_queue.empty():
            try:
                old_session.stream_manager.audio_output_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._log(f"[CLOSE_OLD] Cleared {audio_queue_size} audio chunks from queue")

        # Stop recordings immediately
        if old_session.input_audio_recorder:
            old_session.input_audio_recorder.stop_recording()
        if old_session.output_audio_recorder:
            old_session.output_audio_recorder.stop_recording()

        # Schedule the actual stream close in background (non-blocking)
        asyncio.create_task(self._close_stream_in_background(old_session))

        self._log(f"[CLOSE_OLD] {old_session.session_id} marked as closed, stream closing in background")
        self._log("=" * 80)
        self._log("[TRANSITION] Complete - new session is active")
        self._log("=" * 80)

    async def _close_stream_in_background(self, session):
        """Close the stream in the background without blocking"""
        try:
            await session.stream_manager.send_audio_content_end_event()
            await session.stream_manager.send_prompt_end_event()
            await session.stream_manager.send_session_end_event()
            self._log(f"[CLOSE_BG] Sent close events for {session.session_id}")

            if session.stream_manager.stream_response:
                try:
                    await asyncio.wait_for(
                        session.stream_manager.stream_response.input_stream.close(),
                        timeout=2.0
                    )
                    self._log(f"[CLOSE_BG] Stream closed for {session.session_id}")
                except asyncio.TimeoutError:
                    self._log(f"[CLOSE_BG] Stream close timed out for {session.session_id}")
                except Exception as e:
                    self._log(f"[CLOSE_BG] Stream close error for {session.session_id}: {e}")

            session.state = SessionState.CLOSED
            self._log(f"[CLOSE_BG] {session.session_id} fully closed")
        except Exception as e:
            self._log(f"[CLOSE_BG] Error closing {session.session_id}: {e}")

    async def _send_buffered_audio_to_next_session(self):
        """Send buffered audio to the next session"""
        if not self.next_session:
            return

        if self.audio_buffer.is_empty():
            self._log("No buffered audio to send")
            # Stop initialization audio recording if no buffer
            if self.next_session.recording_initialization_audio:
                self._stop_initialization_recording(self.next_session)
            return

        buffer_duration = self.audio_buffer.total_size / (16000 * 2)  # bytes / (sample_rate * sample_width)
        self._log(f"Sending {len(self.audio_buffer.buffer)} buffered audio chunks (~{buffer_duration:.2f}s) to next session")

        # Note: audio content start was already sent in _initiate_transition()
        # So we just send the buffered audio chunks directly

        # Send all buffered chunks and record them to both files
        chunks_sent = 0
        for chunk in self.audio_buffer.get_all_chunks():
            # Send to session
            self.next_session.stream_manager.add_audio_chunk(chunk)

            # Record to BOTH input audio file AND initialization audio file
            # This ensures the main input recording has the complete audio sent to the model
            if self.next_session.input_audio_recorder:
                self.next_session.input_audio_recorder.write_chunk(chunk)

            # Also record to initialization audio file for debugging/validation
            if self.next_session.initialization_audio_recorder:
                self.next_session.initialization_audio_recorder.write_chunk(chunk)

            # NOTE: Don't record to conversation file here!
            # This buffered audio was already recorded in real-time via add_audio_chunk()
            # Recording it again would create duplicates in the conversation file

            chunks_sent += 1

        self._log(f"Buffered audio sent: {chunks_sent} chunks (recorded to both input and initialization files)")

        # Stop initialization audio recording after buffer is sent
        # Any additional audio is regular real-time audio, not initialization
        if self.next_session.recording_initialization_audio:
            self._stop_initialization_recording(self.next_session)

        # Don't clear buffer immediately - keep collecting as audio continues
        # Buffer will naturally roll over old data as new audio comes in

    def _stop_initialization_recording(self, session: SessionInfo):
        """Stop recording initialization audio for a session"""
        if session.initialization_audio_recorder:
            session.initialization_audio_recorder.stop_recording()
            session.recording_initialization_audio = False
            self._log(f"Stopped recording initialization audio for {session.session_id}")

    async def _rename_session_recordings(self, session: SessionInfo):
        """Rename session recording files to include model session ID"""
        if not session.model_session_id:
            return

        # Store the desired final filename but don't rename yet
        # We'll rename when the recording is stopped to avoid audio loss
        if session.input_audio_recorder:
            new_filename = f"{session.session_id}_{session.model_session_id}_input.wav"
            session.input_audio_recorder.final_path = os.path.join(self.recording_dir, new_filename)
            self._log(f"Will rename input recording to: {new_filename} when stopped")

        # Store the desired final filename but don't rename yet
        if session.output_audio_recorder:
            new_filename = f"{session.session_id}_{session.model_session_id}_output.wav"
            session.output_audio_recorder.final_path = os.path.join(self.recording_dir, new_filename)
            self._log(f"Will rename output recording to: {new_filename} when stopped")

        # Rename initialization audio file (if it exists and was recorded)
        if session.initialization_audio_recorder:
            old_path = session.initialization_audio_recorder.file_path
            if os.path.exists(old_path):
                new_filename = f"{session.session_id}_{session.model_session_id}_initialization_audio.wav"
                new_path = os.path.join(self.recording_dir, new_filename)

                try:
                    os.rename(old_path, new_path)
                    self._log(f"Renamed initialization audio: {new_filename}")
                    session.initialization_audio_recorder.file_path = new_path
                except Exception as e:
                    self._log(f"Error renaming initialization audio: {e}")


    async def _save_conversation_history(self, session: SessionInfo):
        """Save conversation history to a JSON file"""
        if not self.recording_dir:
            return

        history_file = os.path.join(
            self.recording_dir,
            f"{session.session_id}_conversation_history.json"
        )

        history_data = {
            "session_id": session.session_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "num_messages": len(self.conversation_history.messages),
            "messages": self.conversation_history.messages
        }

        try:
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
            self._log(f"Saved conversation history to: {session.session_id}_conversation_history.json")
        except Exception as e:
            self._log(f"Error saving conversation history: {e}")

    def add_audio_chunk(self, audio_chunk: bytes):
        """Route audio chunk to current active session and record"""
        self.audio_chunk_count += 1

        # Log every 100 chunks to track audio routing
        if self.audio_chunk_count % 100 == 0:
            session_id = self.current_session.session_id if self.current_session else "None"
            self._log(f"[AUDIO_ROUTING] Routing chunk #{self.audio_chunk_count} to {session_id}")

        if self.is_buffering:
            self.audio_buffer.add_chunk(audio_chunk)

        if self.current_session and self.current_session.state == SessionState.ACTIVE:
            self.current_session.stream_manager.add_audio_chunk(audio_chunk)
            if self.current_session.input_audio_recorder:
                self.current_session.input_audio_recorder.write_chunk(audio_chunk)
        else:
            if not self.current_session:
                self._log("[AUDIO_ROUTING] ERROR: No current_session!")
            elif self.current_session.state != SessionState.ACTIVE:
                self._log(f"[AUDIO_ROUTING] ERROR: current_session state is {self.current_session.state}, not ACTIVE!")

    async def get_output_audio(self) -> Optional[bytes]:
        """Get output audio from active session"""
        if (self.next_session and
            self.next_session.received_completion_start and
            self.next_session.state == SessionState.ACTIVE):

            if self.current_session and self.current_session.state == SessionState.ACTIVE:
                try:
                    audio_data = await asyncio.wait_for(
                        self.current_session.stream_manager.audio_output_queue.get(),
                        timeout=0.01
                    )
                    if self.current_session.output_audio_recorder:
                        self.current_session.output_audio_recorder.write_chunk(audio_data)
                    return audio_data
                except asyncio.TimeoutError:
                    pass

            if self.next_session:
                try:
                    audio_data = await asyncio.wait_for(
                        self.next_session.stream_manager.audio_output_queue.get(),
                        timeout=0.01
                    )
                    if self.next_session.output_audio_recorder:
                        self.next_session.output_audio_recorder.write_chunk(audio_data)
                    return audio_data
                except asyncio.TimeoutError:
                    return None

        if self.current_session and self.current_session.state == SessionState.ACTIVE:
            try:
                audio_data = await asyncio.wait_for(
                    self.current_session.stream_manager.audio_output_queue.get(),
                    timeout=0.01
                )
                if self.current_session.output_audio_recorder:
                    self.current_session.output_audio_recorder.write_chunk(audio_data)
                return audio_data
            except asyncio.TimeoutError:
                pass

        return None

    def get_active_stream_manager(self):
        """Get the currently active stream manager"""
        if self.transition_ready and self.next_session:
            return self.next_session.stream_manager
        elif self.current_session:
            return self.current_session.stream_manager
        return None

    async def send_audio_content_start_event(self):
        """Send audio content start event to the active session"""
        if self.current_session:
            await self.current_session.stream_manager.send_audio_content_start_event()

    async def close_all_sessions(self):
        """Close all sessions"""
        self._log("Closing all sessions")

        # Cancel all monitoring tasks
        if hasattr(self, 'monitor_task') and self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, 'monitor_old_session_task') and self.monitor_old_session_task:
            self.monitor_old_session_task.cancel()
            try:
                await self.monitor_old_session_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, 'monitor_next_session_task') and self.monitor_next_session_task:
            self.monitor_next_session_task.cancel()
            try:
                await self.monitor_next_session_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, 'next_session_monitor_task') and self.next_session_monitor_task:
            self.next_session_monitor_task.cancel()
            try:
                await self.next_session_monitor_task
            except asyncio.CancelledError:
                pass

        if self.next_session:
            if self.next_session.input_audio_recorder:
                self.next_session.input_audio_recorder.stop_recording()
            if self.next_session.output_audio_recorder:
                self.next_session.output_audio_recorder.stop_recording()

            try:
                # Send close events but don't cancel tasks
                await self.next_session.stream_manager.send_audio_content_end_event()
                await self.next_session.stream_manager.send_prompt_end_event()
                await self.next_session.stream_manager.send_session_end_event()

                # Set is_active = False to stop receive loop
                self.next_session.stream_manager.is_active = False

                # Close input stream
                if self.next_session.stream_manager.stream_response:
                    await self.next_session.stream_manager.stream_response.input_stream.close()

                # Wait for natural exit
                await asyncio.sleep(0.2)
            except Exception as e:
                self._log(f"Error closing next session: {e}")

            self.next_session.state = SessionState.CLOSED

        if self.current_session:
            self._log(f"Stopping recordings for {self.current_session.session_id}")
            if self.current_session.input_audio_recorder:
                self._log(f"Stopping input recorder for {self.current_session.session_id}")
                self.current_session.input_audio_recorder.stop_recording()
            if self.current_session.output_audio_recorder:
                self._log(f"Stopping output recorder for {self.current_session.session_id}")
                self.current_session.output_audio_recorder.stop_recording()

            try:
                # Send close events but don't cancel tasks
                await self.current_session.stream_manager.send_audio_content_end_event()
                await self.current_session.stream_manager.send_prompt_end_event()
                await self.current_session.stream_manager.send_session_end_event()

                # Set is_active = False to stop receive loop
                self.current_session.stream_manager.is_active = False

                # Close input stream
                if self.current_session.stream_manager.stream_response:
                    await self.current_session.stream_manager.stream_response.input_stream.close()

                # Wait for natural exit
                await asyncio.sleep(0.2)
            except Exception as e:
                self._log(f"Error closing current session: {e}")

            self.current_session.state = SessionState.CLOSED

        self._log("All sessions closed")
