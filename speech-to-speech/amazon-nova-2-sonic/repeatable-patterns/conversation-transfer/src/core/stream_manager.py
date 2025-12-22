"""Bedrock streaming manager for bidirectional communication."""
import asyncio
import base64
import json
import uuid
from typing import List, Dict, Any, Optional

from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import Config
from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver

from src.core.config import MAX_TOKENS, TOP_P, TEMPERATURE
from src.core.utils import debug_print, time_it_async
from src.core.event_templates import EventTemplates
from src.core.tool_processor import ToolProcessor


class BedrockStreamManager:
    """Manages bidirectional streaming with AWS Bedrock."""
    
    def __init__(
        self,
        model_id: str,
        region: str,
        voice_id: str = 'matthew',
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        active_agent: str = 'support'
    ):
        self.model_id = model_id
        self.region = region
        self.voice_id = voice_id
        self.system_prompt = system_prompt
        self.conversation_history = conversation_history or []
        self.active_agent = active_agent
        
        # Queues
        self.audio_input_queue = asyncio.Queue()
        self.audio_output_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        
        # State
        self.is_active = False
        self.barge_in = False
        self.switch_requested = False
        self.new_voice = None
        
        # Session IDs
        self.prompt_name = str(uuid.uuid4())
        self.content_name = str(uuid.uuid4())
        self.audio_content_name = str(uuid.uuid4())
        
        # Tool handling
        self.tool_processor = ToolProcessor()
        self.pending_tool_tasks = {}
        self.tool_use_content = ""
        self.tool_use_id = ""
        self.tool_name = ""
        
        # Response tracking
        self.display_assistant_text = False
        self.role = None
        
        # Client
        self.bedrock_client = None
        self.stream_response = None
        self.response_task = None
    
    def _initialize_client(self):
        """Initialize Bedrock client."""
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
        self.bedrock_client = BedrockRuntimeClient(config=config)
    
    async def initialize_stream(self):
        """Initialize bidirectional stream."""
        if not self.bedrock_client:
            self._initialize_client()
        
        try:
            self.stream_response = await time_it_async(
                "invoke_model_with_bidirectional_stream",
                lambda: self.bedrock_client.invoke_model_with_bidirectional_stream(
                    InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
                )
            )
            self.is_active = True
            
            # Send initialization sequence
            await self._send_initialization_events()
            
            # Start response processing
            self.response_task = asyncio.create_task(self._process_responses())
            asyncio.create_task(self._process_audio_input())
            
            await asyncio.sleep(0.1)
            debug_print("Stream initialized")
            return self
            
        except Exception as e:
            self.is_active = False
            print(f"Failed to initialize stream: {e}")
            raise
    
    async def _send_initialization_events(self):
        """Send initialization event sequence."""
        system_prompt = self.system_prompt or "You are a friend engaging in natural real-time conversation."
        
        events = [
            EventTemplates.start_session(),
            EventTemplates.prompt_start(self.prompt_name, self.voice_id, self.active_agent, []),
            EventTemplates.text_content_start(self.prompt_name, self.content_name, "SYSTEM"),
            EventTemplates.text_input(self.prompt_name, self.content_name, system_prompt),
            EventTemplates.content_end(self.prompt_name, self.content_name)
        ]
        
        for event in events:
            await self.send_raw_event(event)
            await asyncio.sleep(0.1)
        
        # Send conversation history
        if self.conversation_history:
            print(f"📤 Sending conversation history: {len(self.conversation_history)} messages")
            debug_print(f"Sending {len(self.conversation_history)} history messages")
            self.conversation_history = self.conversation_history[:-1]
            # Remove assistant messages from the start
            while self.conversation_history and self.conversation_history[0].get('role') == 'ASSISTANT':
                self.conversation_history.pop(0)
            for msg in self.conversation_history:
                await self._send_history_message(msg)

        speak_first_content_name = str(uuid.uuid4())
        speak_first_events = [
            EventTemplates.text_content_start(self.prompt_name,content_name=speak_first_content_name, role='USER', interactive=True),
            EventTemplates.text_input(self.prompt_name, speak_first_content_name, 'Greet the user with his name and SHORT explanation your role'),
            EventTemplates.content_end(self.prompt_name, speak_first_content_name)
        ]
        for event in speak_first_events:
            await self.send_raw_event(event)
            await asyncio.sleep(0.1)
    
    async def _send_history_message(self, message: Dict[str, str]):
        """Send single history message."""
        history_content_name = str(uuid.uuid4())
        events = [
            EventTemplates.text_content_start(self.prompt_name, history_content_name, message["role"]),
            EventTemplates.text_input(self.prompt_name, history_content_name, message["content"]),
            EventTemplates.content_end(self.prompt_name, history_content_name)
        ]
        
        for event in events:
            await self.send_raw_event(event)
            await asyncio.sleep(0.1)
    
    async def send_raw_event(self, event_json: str):
        """Send raw event to Bedrock."""
        if not self.stream_response or not self.is_active:
            debug_print("Stream not active")
            return
        
        event = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=event_json.encode('utf-8'))
        )
        
        try:
            await self.stream_response.input_stream.send(event)
            if len(event_json) > 200:
                event_type = list(json.loads(event_json).get("event", {}).keys())
                debug_print(f"Sent event: {event_type}")
            else:
                debug_print(f"Sent: {event_json}")
        except Exception as e:
            debug_print(f"Error sending event: {e}")
    
    async def _process_audio_input(self):
        """Process audio input queue."""
        while self.is_active:
            try:
                data = await self.audio_input_queue.get()
                audio_bytes = data.get('audio_bytes')
                if not audio_bytes:
                    continue
                
                blob = base64.b64encode(audio_bytes).decode('utf-8')
                event = EventTemplates.audio_input(self.prompt_name, self.audio_content_name, blob)
                await self.send_raw_event(event)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                debug_print(f"Error processing audio: {e}")
    
    def add_audio_chunk(self, audio_bytes: bytes):
        """Add audio chunk to queue."""
        self.audio_input_queue.put_nowait({
            'audio_bytes': audio_bytes,
            'prompt_name': self.prompt_name,
            'content_name': self.audio_content_name
        })
    
    async def send_audio_content_start_event(self):
        """Send audio content start."""
        event = EventTemplates.content_start(self.prompt_name, self.audio_content_name)
        await self.send_raw_event(event)
    
    async def send_audio_content_end_event(self):
        """Send audio content end."""
        if self.is_active:
            event = EventTemplates.content_end(self.prompt_name, self.audio_content_name)
            await self.send_raw_event(event)
            debug_print("Audio ended")
    
    async def _process_responses(self):
        """Process incoming Bedrock responses."""
        try:
            while self.is_active and not self.switch_requested:
                try:
                    output = await self.stream_response.await_output()
                    result = await output[1].receive()
                    
                    if result.value and result.value.bytes_:
                        await self._handle_response(result.value.bytes_.decode('utf-8'))
                        
                except StopAsyncIteration:
                    break
                except Exception as e:
                    if "InvalidStateError" in str(e) or "CANCELLED" in str(e):
                        debug_print("Stream cancelled")
                        break
                    elif "ValidationException" in str(e):
                        print(f"Validation error: {e}")
                        break
                    else:
                        print(f"Error receiving response: {e}")
                        break
        except Exception as e:
            print(f"Response processing error: {e}")
        finally:
            self.is_active = False
    
    async def _handle_response(self, response_data: str):
        """Handle single response."""
        try:
            json_data = json.loads(response_data)
            
            if 'event' not in json_data:
                await self.output_queue.put({"raw_data": response_data})
                return
            
            event = json_data['event']
            
            if 'completionStart' in event:
                debug_print(f"Completion start: {event}")
            elif 'contentStart' in event:
                self._handle_content_start(event['contentStart'])
            elif 'textOutput' in event:
                self._handle_text_output(event['textOutput'])
            elif 'audioOutput' in event:
                await self._handle_audio_output(event['audioOutput'])
            elif 'toolUse' in event:
                await self._handle_tool_use(event['toolUse'])
            elif 'contentEnd' in event:
                await self._handle_content_end(event['contentEnd'])
            elif 'completionEnd' in event:
                debug_print("Completion end")
            elif 'usageEvent' in event:
                debug_print(f"Usage: {event}")
            
            await self.output_queue.put(json_data)
            
        except json.JSONDecodeError:
            await self.output_queue.put({"raw_data": response_data})
    
    def _handle_content_start(self, content_start: Dict[str, Any]):
        """Handle content start event."""
        debug_print("Content start")
        self.role = content_start['role']
        
        if 'additionalModelFields' in content_start:
            try:
                fields = json.loads(content_start['additionalModelFields'])
                self.display_assistant_text = fields.get('generationStage') == 'FINAL'
            except json.JSONDecodeError:
                debug_print("Error parsing additionalModelFields")
    
    def _handle_text_output(self, text_output: Dict[str, Any]):
        """Handle text output event."""
        content = text_output['content']
        role = text_output['role']
        
        if '{ "interrupted" : true }' in content:
            debug_print("Barge-in detected")
            self.barge_in = True
        
        if (self.role == "ASSISTANT" and self.display_assistant_text) or self.role == "USER":
            self.conversation_history.append({"role": role, "content": content})
        if (self.role == "ASSISTANT" and not self.display_assistant_text) or self.role == "USER":
            print(f"{role.title()}: {content}")
    
    async def _handle_audio_output(self, audio_output: Dict[str, Any]):
        """Handle audio output event."""
        audio_bytes = base64.b64decode(audio_output['content'])
        await self.audio_output_queue.put(audio_bytes)
    
    async def _handle_tool_use(self, tool_use: Dict[str, Any]):
        """Handle tool use event."""
        self.tool_use_content = tool_use
        self.tool_name = tool_use['toolName']
        self.tool_use_id = tool_use['toolUseId']
        
        if self.tool_name == 'switch_agent':
            content_data = json.loads(tool_use['content'])
            self.new_voice = content_data.get("role", "support").lower()
            await asyncio.sleep(0.1)
            self.switch_requested = True
            print(f"🎯 Switching to: {self.new_voice}")
        else:
            print(f"🎯 Tool use: {self.tool_name}")
            debug_print(f"Tool: {self.tool_name}, ID: {self.tool_use_id}")
    
    async def _handle_content_end(self, content_end: Dict[str, Any]):
        """Handle content end event."""
        if content_end.get('type') == 'TOOL':
            debug_print("Processing tool")
            self._handle_tool_request(self.tool_name, self.tool_use_content, self.tool_use_id)
        else:
            debug_print("Content end")
    
    def _handle_tool_request(self, tool_name: str, tool_content: Dict[str, Any], tool_use_id: str):
        """Handle tool request asynchronously."""
        content_name = str(uuid.uuid4())
        task = asyncio.create_task(
            self._execute_tool_and_send_result(tool_name, tool_content, tool_use_id, content_name)
        )
        self.pending_tool_tasks[content_name] = task
        task.add_done_callback(lambda t: self._handle_tool_completion(t, content_name))
    
    def _handle_tool_completion(self, task, content_name: str):
        """Handle tool task completion."""
        self.pending_tool_tasks.pop(content_name, None)
        if task.done() and not task.cancelled():
            exception = task.exception()
            if exception:
                debug_print(f"Tool task failed: {exception}")
    
    async def _execute_tool_and_send_result(
        self,
        tool_name: str,
        tool_content: Dict[str, Any],
        tool_use_id: str,
        content_name: str
    ):
        """Execute tool and send result."""
        try:
            debug_print(f"Executing tool: {tool_name}")
            result = await self.tool_processor.process_tool_async(tool_name, tool_content)
            
            await self.send_raw_event(EventTemplates.tool_content_start(self.prompt_name, content_name, tool_use_id))
            await self.send_raw_event(EventTemplates.tool_result(self.prompt_name, content_name, result))
            await self.send_raw_event(EventTemplates.content_end(self.prompt_name, content_name))
            
            debug_print(f"Tool complete: {tool_name}")
        except Exception as e:
            debug_print(f"Tool error: {e}")
            try:
                error_result = {"error": f"Tool failed: {e}"}
                await self.send_raw_event(EventTemplates.tool_content_start(self.prompt_name, content_name, tool_use_id))
                await self.send_raw_event(EventTemplates.tool_result(self.prompt_name, content_name, error_result))
                await self.send_raw_event(EventTemplates.content_end(self.prompt_name, content_name))
            except Exception as send_error:
                debug_print(f"Failed to send error: {send_error}")
    
    async def close(self):
        """Close stream and cleanup."""
        if not self.is_active:
            return
        
        debug_print("Closing stream")
        self.is_active = False
        
        for task in self.pending_tool_tasks.values():
            task.cancel()
        
        if self.response_task and not self.response_task.done():
            self.response_task.cancel()
        
        try:
            await self.send_audio_content_end_event()
            await self.send_raw_event(EventTemplates.prompt_end(self.prompt_name))
            await self.send_raw_event(EventTemplates.session_end())
        except Exception as e:
            debug_print(f"Error during close: {e}")
        
        if self.stream_response:
            try:
                await self.stream_response.input_stream.close()
            except Exception as e:
                debug_print(f"Error closing input stream: {e}")
        
        debug_print("Stream closed")
