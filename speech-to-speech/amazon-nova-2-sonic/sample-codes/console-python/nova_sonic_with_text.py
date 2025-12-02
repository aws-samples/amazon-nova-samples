import os
import asyncio
import base64
import json
import uuid
import warnings
import pyaudio
import pytz
import random
import hashlib
import datetime
import time
import inspect
from rx.subject import Subject
from rx import operators as ops
from rx.scheduler.eventloop import AsyncIOScheduler
from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import Config
from smithy_aws_core.identity.environment import EnvironmentCredentialsResolver

# Suppress warnings
warnings.filterwarnings("ignore")
# Audio configuration
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK_SIZE = 1024  # Number of frames per buffer

# Debug mode flag
DEBUG = False

def debug_print(message):
    """Print only if debug mode is enabled"""
    if DEBUG:
        functionName = inspect.stack()[1].function
        if  functionName == 'time_it' or functionName == 'time_it_async':
            functionName = inspect.stack()[2].function
        print('{:%Y-%m-%d %H:%M:%S.%f}'.format(datetime.datetime.now())[:-3] + ' ' + functionName + ' ' + message)

def time_it(label, methodToRun):
    start_time = time.perf_counter()
    result = methodToRun()
    end_time = time.perf_counter()
    debug_print(f"Execution time for {label}: {end_time - start_time:.4f} seconds")
    return result

async def time_it_async(label, methodToRun):
    start_time = time.perf_counter()
    result = await methodToRun()
    end_time = time.perf_counter()
    debug_print(f"Execution time for {label}: {end_time - start_time:.4f} seconds")
    return result


class ToolProcessor:
    def __init__(self):
        # ThreadPoolExecutor could be used for complex implementations
        self.tasks = {}
    
    async def process_tool_async(self, tool_name, tool_content):
        """Process a tool call asynchronously and return the result"""
        # Create a unique task ID
        task_id = str(uuid.uuid4())
        
        # Create and store the task
        task = asyncio.create_task(self._run_tool(tool_name, tool_content))
        self.tasks[task_id] = task
        
        try:
            # Wait for the task to complete
            result = await task
            return result
        finally:
            # Clean up the task reference
            if task_id in self.tasks:
                del self.tasks[task_id]
    
    async def _run_tool(self, tool_name, tool_content):
        """Internal method to execute the tool logic"""
        debug_print(f"Processing tool: {tool_name}")
        tool = tool_name.lower()
        
        if tool == "getdateandtimetool":
            # Get current date in PST timezone
            pst_timezone = pytz.timezone("America/Los_Angeles")
            pst_date = datetime.datetime.now(pst_timezone)
            
            return {
                "formattedTime": pst_date.strftime("%I:%M %p"),
                "date": pst_date.strftime("%Y-%m-%d"),
                "year": pst_date.year,
                "month": pst_date.month,
                "day": pst_date.day,
                "dayOfWeek": pst_date.strftime("%A").upper(),
                "timezone": "PST"
            }
        
        elif tool == "trackordertool":
            # Simulate a long-running operation
            debug_print(f"TrackOrderTool starting operation that will take time...")
            await asyncio.sleep(10)  # Non-blocking sleep to simulate processing time
            
            # Extract order ID from toolUseContent
            content = tool_content.get("content", {})
            content_data = json.loads(content)
            order_id = content_data.get("orderId", "")
            request_notifications = content_data.get("requestNotifications", False)
            
            # Convert order_id to string if it's an integer
            if isinstance(order_id, int):
                order_id = str(order_id)
            # Validate order ID format
            if not order_id or not isinstance(order_id, str):
                return {
                    "error": "Invalid order ID format",
                    "orderStatus": "",
                    "estimatedDelivery": "",
                    "lastUpdate": ""
                }
            
            # Create deterministic randomness based on order ID
            # This ensures the same order ID always returns the same status
            seed = int(hashlib.md5(order_id.encode(), usedforsecurity=False).hexdigest(), 16) % 10000
            random.seed(seed)
            
            # Rest of the order tracking logic
            statuses = [
                "Order received", 
                "Processing", 
                "Preparing for shipment",
                "Shipped",
                "In transit", 
                "Out for delivery",
                "Delivered",
                "Delayed"
            ]
            
            weights = [10, 15, 15, 20, 20, 10, 5, 3]
            status = random.choices(statuses, weights=weights, k=1)[0]
            
            # Generate delivery date logic
            today = datetime.datetime.now()
            if status == "Delivered":
                delivery_days = -random.randint(0, 3)
                estimated_delivery = (today + datetime.timedelta(days=delivery_days)).strftime("%Y-%m-%d")
            elif status == "Out for delivery":
                estimated_delivery = today.strftime("%Y-%m-%d")
            else:
                delivery_days = random.randint(1, 10)
                estimated_delivery = (today + datetime.timedelta(days=delivery_days)).strftime("%Y-%m-%d")

            # Handle notification request
            notification_message = ""
            if request_notifications and status != "Delivered":
                notification_message = f"You will receive notifications for order {order_id}"

            # Return tracking information
            tracking_info = {
                "orderStatus": status,
                "orderNumber": order_id,
                "notificationStatus": notification_message
            }

            # Add appropriate fields based on status
            if status == "Delivered":
                tracking_info["deliveredOn"] = estimated_delivery
            elif status == "Out for delivery":
                tracking_info["expectedDelivery"] = "Today"
            else:
                tracking_info["estimatedDelivery"] = estimated_delivery

            # Add location information based on status
            if status == "In transit":
                tracking_info["currentLocation"] = "Distribution Center"
            elif status == "Delivered":
                tracking_info["deliveryLocation"] = "Front Door"
                
            # Add additional info for delayed status
            if status == "Delayed":
                tracking_info["additionalInfo"] = "Weather delays possible"
                
            debug_print(f"TrackOrderTool completed successfully")
            return tracking_info
        else:
            return {
                "error": f"Unsupported tool: {tool_name}"
            }
        
class BedrockStreamManager:
    """Manages bidirectional streaming with AWS Bedrock using RxPy for event processing"""
    
    # Event templates
    START_SESSION_EVENT = '''{
        "event": {
            "sessionStart": {
            "inferenceConfiguration": {
                "maxTokens": 1024,
                "topP": 0.9,
                "temperature": 0.7
                }
            }
        }
    }'''

    def system_prompt(self, prompt):
        """Create a system prompt"""
        systemPrompt = {
            "event": {
               "textInput": {
                    "promptName": self.prompt_name,
                    "contentName": self.content_name,
                    "content": prompt
                }
            }
        }
    
        return json.dumps(systemPrompt)
    
    def chat_prompt(self, content, content_name ):
        """Create a system prompt"""
        systemPrompt = {
            "event": {
               "textInput": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "content": content
                }
            }
        }
    
        return json.dumps(systemPrompt)
    
    def start_prompt(self):
        """Create a promptStart event"""
        get_default_tool_schema = json.dumps({
            "type": "object",
            "properties": {},
            "required": []
        })
        
        prompt_start_event = {
            "event": {
                "promptStart": {
                    "promptName": self.prompt_name,
                    "textOutputConfiguration": {
                        "mediaType": "text/plain"
                    },
                    "audioOutputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": 24000,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "voiceId": "matthew",
                        "encoding": "base64",
                        "audioType": "SPEECH"
                    },
                    "toolUseOutputConfiguration": {
                        "mediaType": "application/json"
                    },
                    "toolConfiguration": {
                        "tools": [
                            {
                                "toolSpec": {
                                    "name": "getDateAndTimeTool",
                                    "description": "Get information about the current date and time",
                                    "inputSchema": {
                                        "json": get_default_tool_schema
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        return json.dumps(prompt_start_event)

    def tool_result_event(self, content_name, content, role):
        """Create a tool result event"""
        if isinstance(content, dict):
            content_json_string = json.dumps(content)
        else:
            content_json_string = content
            
        tool_result_event = {
            "event": {
                "toolResult": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "content": content_json_string
                }
            }
        }
        print(f'Tool result sent: {json.dumps(tool_result_event, indent=2)}')
        return json.dumps(tool_result_event)

    CONTENT_START_EVENT = '''{
        "event": {
            "contentStart": {
            "promptName": "%s",
            "contentName": "%s",
            "type": "AUDIO",
            "interactive": true,
            "role": "USER",
            "audioInputConfiguration": {
                "mediaType": "audio/lpcm",
                "sampleRateHertz": 16000,
                "sampleSizeBits": 16,
                "channelCount": 1,
                "audioType": "SPEECH",
                "encoding": "base64"
                }
            }
        }
    }'''

    AUDIO_EVENT_TEMPLATE = '''{
        "event": {
            "audioInput": {
            "promptName": "%s",
            "contentName": "%s",
            "content": "%s"
            }
        }
    }'''

    TEXT_CONTENT_START_EVENT = '''{
        "event": {
            "contentStart": {
            "promptName": "%s",
            "contentName": "%s",
            "role": "%s",
            "type": "TEXT",
            "interactive": false,
                "textInputConfiguration": {
                    "mediaType": "text/plain"
                }
            }
        }
    }'''

    TEXT_CONTENT_START_EVENT_INTERACTIVE = '''{
        "event": {
            "contentStart": {
            "promptName": "%s",
            "contentName": "%s",
            "role": "%s",
            "type": "TEXT",
            "interactive": true,
                "textInputConfiguration": {
                    "mediaType": "text/plain"
                }
            }
        }
    }'''

    TEXT_INPUT_EVENT = '''{
        "event": {
            "textInput": {
            "promptName": "%s",
            "contentName": "%s",
            "content": "%s"
            }
        }
    }'''

    CONTENT_END_EVENT = '''{
        "event": {
            "contentEnd": {
            "promptName": "%s",
            "contentName": "%s"
            }
        }
    }'''

    PROMPT_END_EVENT = '''{
        "event": {
            "promptEnd": {
            "promptName": "%s"
            }
        }
    }'''

    SESSION_END_EVENT = '''{
        "event": {
            "sessionEnd": {}
        }
    }'''

    TOOL_CONTENT_START_EVENT = '''{
        "event": {
            "contentStart": {
                "promptName": "%s",
                "contentName": "%s",
                "interactive": false,
                "type": "TOOL",
                "role": "TOOL",
                "toolResultInputConfiguration": {
                    "toolUseId": "%s",
                    "type": "TEXT",
                    "textInputConfiguration": {
                        "mediaType": "text/plain"
                    }
                }
            }
        }
    }'''
    
    def __init__(self, model_id='amazon.nova-2-sonic-v1:0', region='us-east-1'):
        """Initialize the stream manager."""
        self.model_id = model_id
        self.region = region
        self.input_subject = Subject()
        self.output_subject = Subject()
        self.audio_subject = Subject()

        self.response_task = None
        self.stream_response = None
        self.is_active = False
        self.barge_in = False
        self.bedrock_client = None
        self.scheduler = None

        # Audio playback components
        self.audio_output_queue = asyncio.Queue()

        # Text response components
        self.display_assistant_text = False
        self.role = None

        # Session information
        self.prompt_name = str(uuid.uuid4())
        self.content_name = str(uuid.uuid4())
        self.audio_content_name = str(uuid.uuid4())
        self.text_content_name = str(uuid.uuid4())
        self.toolUseContent = ""
        self.toolUseId = ""
        self.toolName = ""

        self.tool_processor = ToolProcessor()
        self.pending_tool_tasks = {}

        # Completion event to wait for proper shutdown
        self.completion_event = asyncio.Event()

    def _initialize_client(self):
        """Initialize the Bedrock client."""
        config = Config(
            endpoint_uri= f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        )
        self.bedrock_client = BedrockRuntimeClient(config=config)
    
    async def initialize_stream(self):
        """Initialize the bidirectional stream with Bedrock."""
        if not self.bedrock_client:
            self._initialize_client()
        
        self.scheduler = AsyncIOScheduler(asyncio.get_event_loop())      
        try:
            self.stream_response = await time_it_async("invoke_model_with_bidirectional_stream", lambda : self.bedrock_client.invoke_model_with_bidirectional_stream( InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)))

            self.is_active = True
            default_system_prompt = "You are a warm, professional, and helpful male AI assistant. Give accurate answers that sound natural, direct, and human. Start by answering the user's question clearly in 1–2 sentences. Then, expand only enough to make the answer understandable, staying within 3–5 short sentences total. Avoid sounding like a lecture or essay."
            
            default_speech_prompt = ""
            # example speech prompt for indian
            #default_speech_prompt = "If the input audio/speech contains hindi, then the transcription and response should be in All Devanagari script (Hindi)."

            prompt_event = self.start_prompt()
            text_content_start = self.TEXT_CONTENT_START_EVENT % (self.prompt_name, self.content_name, "SYSTEM")
            text_content = self.system_prompt(default_system_prompt)
            text_content_end = self.CONTENT_END_EVENT % (self.prompt_name, self.content_name)

            speech_content_name = str(uuid.uuid4())
            speech_content_start = self.TEXT_CONTENT_START_EVENT % (self.prompt_name, speech_content_name, "SYSTEM_SPEECH")
            speech_content = self.TEXT_INPUT_EVENT % (self.prompt_name, speech_content_name, default_speech_prompt)
            speech_content_end = self.CONTENT_END_EVENT % (self.prompt_name, speech_content_name)

            history_content_name = str(uuid.uuid4())
            history_content_start = self.TEXT_CONTENT_START_EVENT % (self.prompt_name, history_content_name, "USER")
            history_content = self.chat_prompt("my name is osman", history_content_name)
            history_content_end = self.CONTENT_END_EVENT % (self.prompt_name, history_content_name)

            
            init_events = [self.START_SESSION_EVENT, prompt_event, text_content_start, text_content, text_content_end, speech_content_start, speech_content, speech_content_end, history_content_start, history_content, history_content_end]
            
            for event in init_events:
                await self.send_raw_event(event)
            
            # Start listening for responses
            self.response_task = asyncio.create_task(self._process_responses())
            
            # Set up subscription for input events
            self.input_subject.pipe(
                ops.subscribe_on(self.scheduler)
            ).subscribe(
                on_next=lambda event: asyncio.create_task(self.send_raw_event(event)),
                on_error=lambda e: debug_print(f"Input stream error: {e}")
            )
            
            # Set up subscription for audio chunks
            self.audio_subject.pipe(
                ops.subscribe_on(self.scheduler)
            ).subscribe(
                on_next=lambda audio_data: asyncio.create_task(self._handle_audio_input(audio_data)),
                on_error=lambda e: debug_print(f"Audio stream error: {e}")
            )
            
            debug_print("Stream initialized successfully")
            return self
        except Exception as e:
            self.is_active = False
            print(f"Failed to initialize stream: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    async def send_raw_event(self, event_json):
        """Send a raw event JSON to the Bedrock stream."""
        if not self.stream_response or not self.is_active:
            debug_print("Stream not initialized or closed")
            return
        
        event = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=event_json.encode('utf-8'))
        )
        
        try:
            await self.stream_response.input_stream.send(event)
            # For debugging large events, you might want to log just the type
            if DEBUG:
                if len(event_json) > 200:
                    event_type = json.loads(event_json).get("event", {}).keys()
                    debug_print(f"Sent event type: {list(event_type)}")
                else:
                    debug_print(f"Sent event: {event_json}")
        except Exception as e:
            debug_print(f"Error sending event: {str(e)}")
            if DEBUG:
                import traceback
                traceback.print_exc()
            self.input_subject.on_error(e)
    
    async def send_audio_content_start_event(self):
        """Send a content start event to the Bedrock stream."""
        content_start_event = self.CONTENT_START_EVENT % (self.prompt_name, self.audio_content_name)
        await self.send_raw_event(content_start_event)
    
    async def send_text_content_start_event(self):
        """Send a text content start event to the Bedrock stream."""
        content_start_event = self.TEXT_CONTENT_START_EVENT_INTERACTIVE % (self.prompt_name, self.text_content_name, "USER")
        await self.send_raw_event(content_start_event)
    
    async def send_text_input(self, text):
        """Send text input to the Bedrock stream."""
        if not self.is_active:
            debug_print("Stream is not active")
            return
        
        # Send text content start event
        await self.send_text_content_start_event()
        
        # Send the text input event
        text_event = self.TEXT_INPUT_EVENT % (self.prompt_name, self.text_content_name, text)
        await self.send_raw_event(text_event)
        
        # Send text content end event
        await self.send_text_content_end_event()
        
        debug_print(f"Sent text input: {text}")
    
    async def send_text_content_end_event(self):
        """Send a text content end event to the Bedrock stream."""
        content_end_event = self.CONTENT_END_EVENT % (self.prompt_name, self.text_content_name)
        await self.send_raw_event(content_end_event)
    
    async def _handle_audio_input(self, data):
        """Process audio input before sending it to the stream."""
        audio_bytes = data.get('audio_bytes')
        if not audio_bytes:
            debug_print("No audio bytes received")
            return
        
        try:
            # Ensure the audio is properly formatted
            debug_print(f"Processing audio chunk of size {len(audio_bytes)} bytes")
            
            # Base64 encode the audio data
            blob = base64.b64encode(audio_bytes)
            audio_event = self.AUDIO_EVENT_TEMPLATE % (self.prompt_name, self.audio_content_name, blob.decode('utf-8'))
            
            # Send the event directly
            await self.send_raw_event(audio_event)
        except Exception as e:
            debug_print(f"Error processing audio: {e}")
            if DEBUG:
                import traceback
                traceback.print_exc()
    
    def add_audio_chunk(self, audio_bytes):
        """Add an audio chunk to the stream."""
        self.audio_subject.on_next({
            'audio_bytes': audio_bytes,
            'prompt_name': self.prompt_name,
            'content_name': self.audio_content_name
        })
    
    async def send_audio_content_end_event(self):
        """Send a content end event to the Bedrock stream."""
        if not self.is_active:
            debug_print("Stream is not active")
            return
        
        content_end_event = self.CONTENT_END_EVENT % (self.prompt_name, self.audio_content_name)
        await self.send_raw_event(content_end_event)
        debug_print("Audio ended")
    

    async def send_tool_start_event(self, content_name, tool_use_id):
        """Send a tool content start event to the Bedrock stream."""
        content_start_event = self.TOOL_CONTENT_START_EVENT % (self.prompt_name, content_name, tool_use_id)
        debug_print(f"Sending tool start event: {content_start_event}")  
        await self.send_raw_event(content_start_event)

    async def send_tool_result_event(self, content_name, tool_result):
        """Send a tool content event to the Bedrock stream."""
        tool_result_event = self.tool_result_event(content_name=content_name, content=tool_result, role="TOOL")
        debug_print(f"Sending tool result event: {tool_result_event}")
        await self.send_raw_event(tool_result_event)
    
    async def send_tool_content_end_event(self, content_name):
        """Send a tool content end event to the Bedrock stream."""
        tool_content_end_event = self.CONTENT_END_EVENT % (self.prompt_name, content_name)
        debug_print(f"Sending tool content end event: {tool_content_end_event}")
        await self.send_raw_event(tool_content_end_event)
    
    async def send_prompt_end_event(self):
        """Close the stream and clean up resources."""
        if not self.is_active:
            debug_print("Stream is not active")
            return
        
        prompt_end_event = self.PROMPT_END_EVENT % (self.prompt_name)
        await self.send_raw_event(prompt_end_event)
        debug_print("Prompt ended")
        
    async def send_session_end_event(self):
        """Send a session end event to the Bedrock stream."""
        if not self.is_active:
            debug_print("Stream is not active")
            return

        await self.send_raw_event(self.SESSION_END_EVENT)
        self.is_active = False
        debug_print("Session ended")
    

    async def send_text_with_new_content_name(self, text):
        """Send text input with a new content name for proper multi-turn conversation."""
        # Generate new content name for each text input
        new_text_content_name = str(uuid.uuid4())
        
        # Send text content start event
        content_start_event = self.TEXT_CONTENT_START_EVENT_INTERACTIVE % (
            self.prompt_name, 
            new_text_content_name, 
            "USER"
        )
        await self.send_raw_event(content_start_event)
        
        # Send the text input event
        text_event = self.TEXT_INPUT_EVENT % (
            self.prompt_name, 
            new_text_content_name, 
            text
        )
        await self.send_raw_event(text_event)
        
        # Send text content end event
        content_end_event = self.CONTENT_END_EVENT % (
            self.prompt_name, 
            new_text_content_name
        )
        await self.send_raw_event(content_end_event)
        
        debug_print(f"Sent text input with content name {new_text_content_name}: {text}")
        print(f"📝 Text sent: {text}\n")
    
    async def _process_responses(self):
        """Process incoming responses from Bedrock."""
        try:
            # Keep processing responses until is_active becomes False or stream closes
            while self.is_active:
                try:
                    output = await self.stream_response.await_output()
                    result = await output[1].receive()

                    if result.value and result.value.bytes_:
                        try:
                            response_data = result.value.bytes_.decode('utf-8')
                            json_data = json.loads(response_data)
                            # Handle different response types
                            if 'event' in json_data:
                                if 'contentStart' in json_data['event']:
                                    debug_print("Content start detected")
                                    content_start = json_data['event']['contentStart']
                                    # set role
                                    self.role = content_start['role']
                                    # Check for speculative content
                                    if 'additionalModelFields' in content_start:
                                        try:
                                            additional_fields = json.loads(content_start['additionalModelFields'])
                                            if additional_fields.get('generationStage') == 'SPECULATIVE':
                                                debug_print("Speculative content detected")
                                                self.display_assistant_text = True
                                            else:
                                                self.display_assistant_text = False
                                        except json.JSONDecodeError:
                                            debug_print("Error parsing additionalModelFields")

                                elif 'contentEnd' in json_data['event'] and json_data['event'].get('contentEnd', {}).get('type') == 'TOOL':
                                    debug_print("Tool use content ended - processing tool")
                                    self.handle_tool_request(self.toolName, self.toolUseContent, self.toolUseId)
                                    debug_print("Tool processing started asynchronously")

                                elif 'textOutput' in json_data['event']:
                                    text_content = json_data['event']['textOutput']['content']
                                    # Check if there is a barge-in
                                    if '{ "interrupted" : true }' in text_content:
                                        if DEBUG:
                                            print("Barge-in detected. Stopping audio output.")
                                        self.barge_in = True

                                    if (self.role == "ASSISTANT" and self.display_assistant_text):
                                        print(f"Assistant: {text_content}")
                                    elif (self.role == "USER"):
                                        print(f"User: {text_content}")

                                elif 'toolUse' in json_data['event']:
                                    self.toolUseContent = json_data['event']['toolUse']
                                    self.toolName = json_data['event']['toolUse']['toolName']
                                    self.toolUseId = json_data['event']['toolUse']['toolUseId']
                                    print(f"Tool use detected: {self.toolName} (ID: {self.toolUseId})")

                                elif 'contentEnd' in json_data['event']:
                                    debug_print(f"Content end event: {json_data}")

                                elif 'promptEnd' in json_data['event']:
                                    debug_print("Prompt end event received")

                                elif 'completionEnd' in json_data['event']:
                                    debug_print("Completion end event received - model has finished final response")
                                    # Signal that we've received the completion event
                                    self.completion_event.set()

                                elif 'audioOutput' in json_data['event']:
                                    audio_content = json_data['event']['audioOutput']['content']
                                    audio_bytes = base64.b64decode(audio_content)
                                    await self.audio_output_queue.put(audio_bytes)

                            self.output_subject.on_next(json_data)
                        except json.JSONDecodeError:
                            self.output_subject.on_next({"raw_data": response_data})
                except StopAsyncIteration:
                    # Stream has ended
                    debug_print("Stream ended (StopAsyncIteration)")
                    break
                except Exception as e:
                    debug_print(f"Error receiving response: {e}")
                    self.output_subject.on_error(e)
                    break
        except Exception as e:
            debug_print(f"Response processing error: {e}")
            self.output_subject.on_error(e)
        finally:
            debug_print("Response processing loop exited")
            self.output_subject.on_completed()

    def handle_tool_request(self, tool_name, tool_content, tool_use_id):
        """Handle a tool request asynchronously"""
        tool_content_name = str(uuid.uuid4())
        
        task = asyncio.create_task(self._execute_tool_and_send_result(
            tool_name, tool_content, tool_use_id, tool_content_name))
        
        self.pending_tool_tasks[tool_content_name] = task
        
        task.add_done_callback(
            lambda t: self._handle_tool_task_completion(t, tool_content_name))
    
    def _handle_tool_task_completion(self, task, content_name):
        """Handle the completion of a tool task"""
        if content_name in self.pending_tool_tasks:
            del self.pending_tool_tasks[content_name]
        
        if task.done() and not task.cancelled():
            exception = task.exception()
            if exception:
                debug_print(f"Tool task failed: {str(exception)}")
    
    async def _execute_tool_and_send_result(self, tool_name, tool_content, tool_use_id, content_name):
        """Execute a tool and send the result"""
        try:
            print(f"Starting tool execution: {tool_name}")
            
            # Execute tool and get result
            tool_result = await self.tool_processor.process_tool_async(tool_name, tool_content)
            
            # Send the result
            await self.send_tool_start_event(content_name, tool_use_id)
            await self.send_tool_result_event(content_name, tool_result)
            await self.send_tool_content_end_event(content_name)
            
            debug_print(f"Tool execution complete: {tool_name}, Status: {tool_result.get('status', 'N/A')}")
            
        except Exception as e:
            debug_print(f"Error executing tool {tool_name}: {str(e)}")
            # Send error response
            try:
                error_result = {
                    "status": "error",
                    "error": f"Tool execution failed: {str(e)}"
                }
                
                await self.send_tool_start_event(content_name, tool_use_id)
                await self.send_tool_result_event(content_name, error_result)
                await self.send_tool_content_end_event(content_name)
            except Exception as send_error:
                debug_print(f"Failed to send error response: {str(send_error)}")
    


    async def close(self):
        """Close the stream properly."""
        if not self.is_active:
            return

        debug_print("Starting graceful shutdown sequence...")

        # Complete the subjects (stop sending new data)
        self.input_subject.on_completed()
        self.audio_subject.on_completed()

        # Send end events to signal completion to the model
        try:
            await self.send_audio_content_end_event()
            await self.send_prompt_end_event()
            await self.send_session_end_event()

            # Wait for the completionEnd event from the model with a timeout
            debug_print("Waiting for completionEnd event from model...")
            try:
                await asyncio.wait_for(self.completion_event.wait(), timeout=5.0)
                debug_print("Received completionEnd event, proceeding with cleanup")
            except asyncio.TimeoutError:
                debug_print("Timeout waiting for completionEnd event, proceeding with cleanup anyway")
        except Exception as e:
            debug_print(f"Error during shutdown sequence: {e}")

        # Set is_active to False to signal _process_responses to exit
        debug_print("Setting is_active to False to stop response processing")
        self.is_active = False

        # Wait for the response processing task to complete naturally
        if self.response_task and not self.response_task.done():
            debug_print("Waiting for response processing task to complete...")
            try:
                await asyncio.wait_for(self.response_task, timeout=2.0)
                debug_print("Response processing task completed")
            except asyncio.TimeoutError:
                debug_print("Response processing task did not complete in time, cancelling...")
                self.response_task.cancel()
                try:
                    await self.response_task
                except asyncio.CancelledError:
                    debug_print("Response processing task cancelled")

        # Close the stream
        if self.stream_response:
            await self.stream_response.input_stream.close()

        debug_print("Shutdown sequence complete")

class AudioStreamer:
    """Handles continuous microphone input and audio output using separate streams."""
    
    def __init__(self, stream_manager):
        self.stream_manager = stream_manager
        self.is_streaming = False
        self.loop = asyncio.get_event_loop()

        # Initialize PyAudio
        debug_print("AudioStreamer Initializing PyAudio...")
        self.p = time_it("AudioStreamerInitPyAudio", pyaudio.PyAudio)
        debug_print("AudioStreamer PyAudio initialized")

        # Initialize separate streams for input and output
        # Input stream with callback for microphone
        debug_print("Opening input audio stream...")
        self.input_stream = time_it("AudioStreamerOpenAudio", lambda  : self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=INPUT_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self.input_callback
        ))
        debug_print("input audio stream opened")

        # Output stream for direct writing (no callback)
        debug_print("Opening output audio stream...")
        self.output_stream = time_it("AudioStreamerOpenAudio", lambda  : self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE
        ))

        debug_print("output audio stream opened")

    def input_callback(self, in_data, frame_count, time_info, status):
        """Callback function that schedules audio processing in the asyncio event loop"""
        if self.is_streaming and in_data:
            # Schedule the task in the event loop
            asyncio.run_coroutine_threadsafe(
                self.process_input_audio(in_data), 
                self.loop
            )
        return (None, pyaudio.paContinue)

    async def process_input_audio(self, audio_data):
        """Process a single audio chunk directly"""
        try:
            # Send audio to Bedrock immediately
            self.stream_manager.add_audio_chunk(audio_data)
        except Exception as e:
            if self.is_streaming:
                print(f"Error processing input audio: {e}")
    
    async def play_output_audio(self):
        """Play audio responses from Nova Sonic"""
        while self.is_streaming:
            try:
                # Check for barge-in flag
                if self.stream_manager.barge_in:
                    # Clear the audio queue
                    while not self.stream_manager.audio_output_queue.empty():
                        try:
                            self.stream_manager.audio_output_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    self.stream_manager.barge_in = False
                    # Small sleep after clearing
                    await asyncio.sleep(0.05)
                    continue
                
                # Get audio data from the stream manager's queue
                audio_data = await asyncio.wait_for(
                    self.stream_manager.audio_output_queue.get(),
                    timeout=0.1
                )
                
                if audio_data and self.is_streaming:
                    # Write directly to the output stream in smaller chunks
                    chunk_size = CHUNK_SIZE  # Use the same chunk size as the stream
                    
                    # Write the audio data in chunks to avoid blocking too long
                    for i in range(0, len(audio_data), chunk_size):
                        if not self.is_streaming:
                            break
                        
                        end = min(i + chunk_size, len(audio_data))
                        chunk = audio_data[i:end]
                        
                        # Create a new function that captures the chunk by value
                        def write_chunk(data):
                            return self.output_stream.write(data)
                        
                        # Pass the chunk to the function
                        await asyncio.get_event_loop().run_in_executor(None, write_chunk, chunk)
                        
                        # Brief yield to allow other tasks to run
                        await asyncio.sleep(0.001)
                    
            except asyncio.TimeoutError:
                # No data available within timeout, just continue
                continue
            except Exception as e:
                if self.is_streaming:
                    print(f"Error playing output audio: {str(e)}")
                    import traceback
                    traceback.print_exc()
                await asyncio.sleep(0.05)
    
    async def start_streaming(self):
        """Start streaming audio."""
        if self.is_streaming:
            return
        
        print("Starting audio streaming. Speak into your microphone...")
        print("Press Enter to stop streaming...")
        
        # Send audio content start event
        await time_it_async("send_audio_content_start_event", lambda : self.stream_manager.send_audio_content_start_event())
        
        self.is_streaming = True
        
        # Start the input stream if not already started
        if not self.input_stream.is_active():
            self.input_stream.start_stream()
        
        # Start processing tasks
        self.output_task = asyncio.create_task(self.play_output_audio())
        
        # Wait for user to press Enter to stop
        await asyncio.get_event_loop().run_in_executor(None, input)
        
        # Once input() returns, stop streaming
        await self.stop_streaming()
    
    async def stop_streaming(self):
        """Stop streaming audio."""
        if not self.is_streaming:
            return
            
        self.is_streaming = False

        # Cancel the tasks
        tasks = []
        if hasattr(self, 'input_task') and not self.input_task.done():
            tasks.append(self.input_task)
        
        if hasattr(self, 'output_task') and not self.output_task.done():
            tasks.append(self.output_task)
        
        for task in tasks:
            task.cancel()
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Stop and close the streams
        if self.input_stream:
            if self.input_stream.is_active():
                self.input_stream.stop_stream()
            self.input_stream.close()
        
        if self.output_stream:
            if self.output_stream.is_active():
                self.output_stream.stop_stream()
            self.output_stream.close()
        
        if self.p:
            self.p.terminate()
        print("Audio streaming stopped.")
        await self.stream_manager.close()

class SilentAudioStreamer(AudioStreamer):
    """AudioStreamer that sends silent audio for text-only mode."""
    
    def __init__(self, stream_manager):
        self.stream_manager = stream_manager
        self.is_streaming = False
        self.loop = asyncio.get_event_loop()
        self.silent_task = None
        
        # Initialize PyAudio for output only (no microphone input)
        debug_print("SilentAudioStreamer Initializing PyAudio...")
        self.p = time_it("SilentAudioStreamerInitPyAudio", pyaudio.PyAudio)
        debug_print("SilentAudioStreamer PyAudio initialized")

        # Output stream for audio responses
        debug_print("Opening output audio stream...")
        self.output_stream = time_it("SilentAudioStreamerOpenAudio", lambda: self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE
        ))
        debug_print("output audio stream opened")

    async def start_streaming(self):
        """Start streaming silent audio and playing responses."""
        if self.is_streaming:
            return
        
        print("Starting silent audio streaming for text mode...")
        
        # Send audio content start event
        await time_it_async("send_audio_content_start_event", lambda: self.stream_manager.send_audio_content_start_event())
        
        self.is_streaming = True
        
        # Start silent audio input task and audio output task
        self.silent_task = asyncio.create_task(self._send_silent_audio())
        self.output_task = asyncio.create_task(self.play_output_audio())
        
        # Small delay to ensure streaming is established
        await asyncio.sleep(0.1)
    
    async def _send_silent_audio(self):
        """Send continuous silent audio chunks."""
        # Create silent audio chunk (16-bit PCM, 16kHz, mono)
        silent_chunk_size = CHUNK_SIZE * 2  # 2 bytes per sample for 16-bit
        silent_chunk = b'\x00' * silent_chunk_size
        
        while self.is_streaming:
            try:
                # Send silent audio chunk
                self.stream_manager.add_audio_chunk(silent_chunk)
                
                # Wait for next chunk (maintain ~16kHz sample rate) - reduced delay for better responsiveness
                await asyncio.sleep(0.01)  # 10ms instead of calculated delay
                
            except Exception as e:
                if self.is_streaming:
                    debug_print(f"Error sending silent audio: {e}")
                break

    async def stop_streaming(self):
        """Stop streaming silent audio."""
        if not self.is_streaming:
            return
            
        self.is_streaming = False

        # Cancel the tasks
        tasks = []
        if self.silent_task and not self.silent_task.done():
            tasks.append(self.silent_task)
        
        if hasattr(self, 'output_task') and not self.output_task.done():
            tasks.append(self.output_task)
        
        for task in tasks:
            task.cancel()
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Close the output stream
        if self.output_stream:
            if self.output_stream.is_active():
                self.output_stream.stop_stream()
            self.output_stream.close()
        
        if self.p:
            self.p.terminate()
        
        await self.stream_manager.close()

class MixedModeHandler:
    """Handles mixed mode where real audio streaming happens with text input overlay."""
    
    def __init__(self, stream_manager):
        self.stream_manager = stream_manager
        self.is_active = False
        self.loop = asyncio.get_event_loop()
        self.waiting_for_response = False
        
        # Audio components
        self.p = None
        self.input_stream = None
        self.output_stream = None
        
        # Tasks
        self.output_task = None
        self.text_input_task = None
    
    def _initialize_audio(self):
        """Initialize PyAudio components for mixed mode."""
        debug_print("MixedModeHandler Initializing PyAudio...")
        self.p = time_it("MixedModeHandlerInitPyAudio", pyaudio.PyAudio)
        debug_print("MixedModeHandler PyAudio initialized")

        # Initialize separate streams for input and output
        # Input stream with callback for microphone
        debug_print("Opening input audio stream...")
        self.input_stream = time_it("MixedModeHandlerOpenInputAudio", lambda: self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=INPUT_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self.input_callback
        ))
        debug_print("input audio stream opened")

        # Output stream for direct writing (no callback)
        debug_print("Opening output audio stream...")
        self.output_stream = time_it("MixedModeHandlerOpenOutputAudio", lambda: self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE
        ))
        debug_print("output audio stream opened")

    def input_callback(self, in_data, frame_count, time_info, status):
        """Callback function that schedules audio processing in the asyncio event loop"""
        if self.is_active and in_data:
            # Schedule the task in the event loop
            asyncio.run_coroutine_threadsafe(
                self.process_input_audio(in_data), 
                self.loop
            )
        return (None, pyaudio.paContinue)

    async def process_input_audio(self, audio_data):
        """Process a single audio chunk directly"""
        try:
            # Send audio to Bedrock immediately
            self.stream_manager.add_audio_chunk(audio_data)
        except Exception as e:
            if self.is_active:
                print(f"Error processing input audio: {e}")
    
    async def play_output_audio(self):
        """Play audio responses from Nova Sonic"""
        while self.is_active:
            try:
                # Check for barge-in flag
                if self.stream_manager.barge_in:
                    # Clear the audio queue
                    while not self.stream_manager.audio_output_queue.empty():
                        try:
                            self.stream_manager.audio_output_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    self.stream_manager.barge_in = False
                    # Small sleep after clearing
                    await asyncio.sleep(0.05)
                    continue
                
                # Get audio data from the stream manager's queue
                audio_data = await asyncio.wait_for(
                    self.stream_manager.audio_output_queue.get(),
                    timeout=0.1
                )
                
                if audio_data and self.is_active:
                    # Write directly to the output stream in smaller chunks
                    chunk_size = CHUNK_SIZE  # Use the same chunk size as the stream
                    
                    # Write the audio data in chunks to avoid blocking too long
                    for i in range(0, len(audio_data), chunk_size):
                        if not self.is_active:
                            break
                        
                        end = min(i + chunk_size, len(audio_data))
                        chunk = audio_data[i:end]
                        
                        # Create a new function that captures the chunk by value
                        def write_chunk(data):
                            return self.output_stream.write(data)
                        
                        # Pass the chunk to the function
                        await asyncio.get_event_loop().run_in_executor(None, write_chunk, chunk)
                        
                        # Brief yield to allow other tasks to run
                        await asyncio.sleep(0.001)
                    
            except asyncio.TimeoutError:
                # No data available within timeout, just continue
                continue
            except Exception as e:
                if self.is_active:
                    print(f"Error playing output audio: {str(e)}")
                    import traceback
                    traceback.print_exc()
                await asyncio.sleep(0.05)
    
    async def handle_text_input(self):
        """Handle text input in mixed mode."""
        print("\n=== Mixed Mode Active ===")
        print("🎤 Audio streaming is active - speak into your microphone")
        print("⌨️  You can also type messages:")
        print("   - Type messages and press Enter to send text")
        print("   - Press Enter during assistant response to interrupt")
        print("   - Type 'quit' or 'exit' to end the session")
        print("   - Type 'help' to see commands again")
        print("\nUse both voice and text simultaneously!\n")

        while self.is_active:
            try:
                # Get user input (non-blocking with timeout to allow interruption)
                try:
                    user_input = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: input("You: ")
                        ),
                        timeout=None  # No timeout, but allows for cancellation
                    )
                except asyncio.CancelledError:
                    break

                # Handle special commands
                if user_input.lower() in ['quit', 'exit']:
                    print("\n👋 Goodbye! Ending mixed mode session...")
                    # Don't set is_active = False here - let close() handle it
                    break
                elif user_input.lower() == 'help':
                    print("\n=== Mixed Mode Commands ===")
                    print("🎤 Audio streaming is active - speak into your microphone")
                    print("⌨️  Text input commands:")
                    print("   - Type messages and press Enter to send text")
                    print("   - Press Enter during assistant response to interrupt")
                    print("   - Type 'quit' or 'exit' to end the session")
                    print("   - Type 'help' to see this menu again")
                    print("\nYou can use both voice and text simultaneously!\n")
                    continue
                elif user_input.strip() == '' and self.waiting_for_response:
                    # Interrupt current response
                    print("\n[Interrupting assistant response...]")
                    self.stream_manager.barge_in = True
                    self.waiting_for_response = False
                    continue
                elif user_input.strip() == '':
                    continue
                
                # Send text input to Nova Sonic with new content name for each message
                self.waiting_for_response = True
                await self.stream_manager.send_text_with_new_content_name(user_input)
                
                # Brief pause to allow response to start
                await asyncio.sleep(0.1)
               
                
            except KeyboardInterrupt:
                print("\nMixed mode session interrupted by user")
                break
            except Exception as e:
                print(f"Error in mixed mode text input: {e}")
                if DEBUG:
                    import traceback
                    traceback.print_exc()
                self.waiting_for_response = False
    
    def _initialize_audio(self):
        """Initialize PyAudio and audio streams."""
        debug_print("MixedModeHandler Initializing PyAudio...")
        self.p = time_it("MixedModeHandlerInitPyAudio", pyaudio.PyAudio)
        debug_print("MixedModeHandler PyAudio initialized")

        # Initialize input stream with callback for microphone
        debug_print("Opening input audio stream...")
        self.input_stream = time_it("MixedModeHandlerOpenInputAudio", lambda: self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=INPUT_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self.input_callback
        ))
        debug_print("input audio stream opened")

        # Initialize output stream for audio responses
        debug_print("Opening output audio stream...")
        self.output_stream = time_it("MixedModeHandlerOpenOutputAudio", lambda: self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE
        ))
        debug_print("output audio stream opened")

    def input_callback(self, in_data, frame_count, time_info, status):
        """Callback function that schedules audio processing in the asyncio event loop"""
        if self.is_active and in_data:
            # Schedule the task in the event loop
            asyncio.run_coroutine_threadsafe(
                self.process_input_audio(in_data), 
                self.loop
            )
        return (None, pyaudio.paContinue)

    async def process_input_audio(self, audio_data):
        """Process a single audio chunk directly"""
        try:
            # Send audio to Bedrock immediately
            self.stream_manager.add_audio_chunk(audio_data)
        except Exception as e:
            if self.is_active:
                print(f"Error processing input audio: {e}")
    
    async def play_output_audio(self):
        """Play audio responses from Nova Sonic"""
        while self.is_active:
            try:
                # Check for barge-in flag
                if self.stream_manager.barge_in:
                    # Clear the audio queue
                    while not self.stream_manager.audio_output_queue.empty():
                        try:
                            self.stream_manager.audio_output_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    self.stream_manager.barge_in = False
                    # Small sleep after clearing
                    await asyncio.sleep(0.05)
                    continue
                
                # Get audio data from the stream manager's queue
                audio_data = await asyncio.wait_for(
                    self.stream_manager.audio_output_queue.get(),
                    timeout=0.1
                )
                
                if audio_data and self.is_active:
                    # Write directly to the output stream in smaller chunks
                    chunk_size = CHUNK_SIZE  # Use the same chunk size as the stream
                    
                    # Write the audio data in chunks to avoid blocking too long
                    for i in range(0, len(audio_data), chunk_size):
                        if not self.is_active:
                            break
                        
                        end = min(i + chunk_size, len(audio_data))
                        chunk = audio_data[i:end]
                        
                        # Create a new function that captures the chunk by value
                        def write_chunk(data):
                            return self.output_stream.write(data)
                        
                        # Pass the chunk to the function
                        await asyncio.get_event_loop().run_in_executor(None, write_chunk, chunk)
                        
                        # Brief yield to allow other tasks to run
                        await asyncio.sleep(0.001)
                    
            except asyncio.TimeoutError:
                # No data available within timeout, just continue
                continue
            except Exception as e:
                if self.is_active:
                    print(f"Error playing output audio: {str(e)}")
                    import traceback
                    traceback.print_exc()
                await asyncio.sleep(0.05)
    
    async def start_mixed_mode(self):
        """Start mixed mode with both audio streaming and text input."""
        if self.is_active:
            return
        
        # Initialize audio components
        self._initialize_audio()
        
        # Send audio content start event
        await time_it_async("send_audio_content_start_event", lambda: self.stream_manager.send_audio_content_start_event())
        
        self.is_active = True
        
        # Start the input stream if not already started
        if not self.input_stream.is_active():
            self.input_stream.start_stream()
        
        # Start processing tasks
        self.output_task = asyncio.create_task(self.play_output_audio())
        self.text_input_task = asyncio.create_task(self.handle_text_input())
        
        print("\n🎤 Mixed mode started! Speak into your microphone or type messages below.")
        
        # Wait for text input task to complete (user quits or interrupts)
        try:
            await self.text_input_task
        except asyncio.CancelledError:
            pass
        
        # Stop mixed mode
        await self.stop_mixed_mode()
    
    async def stop_mixed_mode(self):
        """Stop mixed mode and clean up resources."""
        if not self.is_active:
            return
            
        self.is_active = False

        # Cancel the tasks
        tasks = []
        if self.output_task and not self.output_task.done():
            tasks.append(self.output_task)
        
        if self.text_input_task and not self.text_input_task.done():
            tasks.append(self.text_input_task)
        
        for task in tasks:
            task.cancel()
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Stop and close the streams
        if self.input_stream:
            if self.input_stream.is_active():
                self.input_stream.stop_stream()
            self.input_stream.close()
        
        if self.output_stream:
            if self.output_stream.is_active():
                self.output_stream.stop_stream()
            self.output_stream.close()
        
        if self.p:
            self.p.terminate()
        
        await self.stream_manager.close()

class TextInputHandler:
    """Handles text input from terminal and manages conversation flow with interruption support."""
    
    def __init__(self, stream_manager):
        self.stream_manager = stream_manager
        self.is_active = False
        self.audio_streamer = None
        self.silent_streamer = None
        self.input_task = None
        self.waiting_for_response = False
        
    async def start_text_conversation(self):
        """Start a text-based conversation with Nova Sonic using silent audio streaming."""
        self.is_active = True
        
        print("\n=== Nova Sonic Text Chat ===")
        print("Commands:")
        print("  - Type your message and press Enter to send")
        print("  - Press Enter during assistant response to interrupt")
        print("  - Type 'audio' to switch to audio mode")
        print("  - Type 'quit' or 'exit' to end the conversation")
        print("  - Type 'help' to see this menu again")
        print("\nStart chatting!\n")
        
        # Start silent audio streaming to maintain Nova Sonic connection
        self.silent_streamer = SilentAudioStreamer(self.stream_manager)
        await self.silent_streamer.start_streaming()
        
        try:
            # Start continuous input handling
            self.input_task = asyncio.create_task(self._handle_continuous_input())
            
            # Wait for the input task to complete
            await self.input_task
            
        finally:
            # Stop silent streaming
            if self.silent_streamer:
                await self.silent_streamer.stop_streaming()
        
        self.is_active = False
        await self.stream_manager.close()
    
    async def _handle_continuous_input(self):
        """Handle continuous text input with interruption capability."""
        while self.is_active:
            try:
                # Get user input (non-blocking with timeout to allow interruption)
                try:
                    user_input = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: input("You: ")
                        ),
                        timeout=None  # No timeout, but allows for cancellation
                    )
                except asyncio.CancelledError:
                    break

                # Handle special commands
                if user_input.lower() in ['quit', 'exit']:
                    print("\n👋 Goodbye! Ending text conversation...")
                    # Don't set is_active = False here - let close() handle it
                    break
                elif user_input.lower() == 'help':
                    print("\nCommands:")
                    print("  - Type your message and press Enter to send")
                    print("  - Press Enter during assistant response to interrupt")
                    print("  - Type 'audio' to switch to audio mode")
                    print("  - Type 'quit' or 'exit' to end the conversation")
                    print("  - Type 'help' to see this menu again\n")
                    continue
                elif user_input.lower() == 'audio':
                    await self.switch_to_audio_mode()
                    continue
                elif user_input.strip() == '' and self.waiting_for_response:
                    # Interrupt current response
                    print("\n[Interrupting assistant response...]")
                    self.stream_manager.barge_in = True
                    self.waiting_for_response = False
                    continue
                elif user_input.strip() == '':
                    continue
                
                # Send text input to Nova Sonic with new content name for each message
                self.waiting_for_response = False
                await self.stream_manager.send_text_with_new_content_name(user_input)
                
                # Brief pause to allow response to start
                await asyncio.sleep(0.1)
                
                
            except KeyboardInterrupt:
                print("\nConversation interrupted by user")
                break
            except Exception as e:
                print(f"Error in text conversation: {e}")
                if DEBUG:
                    import traceback
                    traceback.print_exc()
                self.waiting_for_response = False
    

    
    async def switch_to_audio_mode(self):
        """Switch from text mode to audio mode."""
        print("\nSwitching to audio mode...")
        
        # Initialize audio streamer if not already done
        if not self.audio_streamer:
            self.audio_streamer = AudioStreamer(self.stream_manager)
        
        # Start audio streaming
        await self.audio_streamer.start_streaming()
        
        # After audio mode ends, return to text mode
        print("\nReturning to text mode...")
        print("Continue typing your messages:\n")

async def main_with_mode_selection(debug=False):
    """Main function with mode selection (text or audio)."""
    global DEBUG
    DEBUG = debug

    # Create stream manager
    stream_manager = BedrockStreamManager(model_id='amazon.nova-2-sonic-v1:0', region='us-east-1')

    # Initialize the stream
    await time_it_async("initialize_stream", stream_manager.initialize_stream)

    try:
        print("\n=== Nova Sonic Interactive Chat ===")
        print("Choose your interaction mode:")
        print("1. Text chat (type messages)")
        print("2. Audio chat (speak into microphone)")
        print("3. Mixed mode (real audio streaming + text input overlay)")
        
        while True:
            try:
                choice = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: input("\nEnter your choice (1-3): ")
                )
                
                if choice == '1':
                    # Text-only mode
                    text_handler = TextInputHandler(stream_manager)
                    await text_handler.start_text_conversation()
                    break
                elif choice == '2':
                    # Audio-only mode
                    audio_streamer = AudioStreamer(stream_manager)
                    await audio_streamer.start_streaming()
                    break
                elif choice == '3':
                    # Mixed mode (real audio streaming + text input overlay)
                    mixed_handler = MixedModeHandler(stream_manager)
                    await mixed_handler.start_mixed_mode()
                    break
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
        
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        # Clean up
        await stream_manager.close()


async def main_mixed_mode(debug=False):
    """Main function with mixed mode (text and audio)."""
    global DEBUG
    DEBUG = debug

    # Create stream manager
    stream_manager = BedrockStreamManager(model_id='amazon.nova-2-sonic-v1:0', region='us-east-1')

    # Initialize the stream
    await time_it_async("initialize_stream", stream_manager.initialize_stream)

    try:
        mixed_handler = MixedModeHandler(stream_manager)
        await mixed_handler.start_mixed_mode()
        
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        # Clean up
        await stream_manager.close()


async def main_audio_only(debug=False):
    """Original main function for audio-only mode."""
    global DEBUG
    DEBUG = debug

    # Create stream manager
    stream_manager = BedrockStreamManager(model_id='amazon.nova-2-sonic-v1:0', region='us-east-1')

    # Create audio streamer
    audio_streamer = AudioStreamer(stream_manager)

    # Initialize the stream
    await time_it_async("initialize_stream", stream_manager.initialize_stream)

    try:
        # This will run until the user presses Enter
        await audio_streamer.start_streaming()
        
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        # Clean up
        await audio_streamer.stop_streaming()

async def main_text_only(debug=False):
    """Main function for text-only mode."""
    global DEBUG
    DEBUG = debug

    # Create stream manager
    stream_manager = BedrockStreamManager(model_id='amazon.nova-2-sonic-v1:0', region='us-east-1')

    # Initialize the stream
    await time_it_async("initialize_stream", stream_manager.initialize_stream)

    try:
        # Start text conversation
        text_handler = TextInputHandler(stream_manager)
        await text_handler.start_text_conversation()
        
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        # Clean up
        await stream_manager.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Nova Sonic Python Streaming with Text Input Support')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--mode', choices=['text', 'audio', 'mixed', "select"], default='select',
                       help='Interaction mode: text (text only), audio (audio only), mixed (interactive selection), default is the selection')
    args = parser.parse_args()
    
    # Set your AWS credentials here or use environment variables
    # os.environ['AWS_ACCESS_KEY_ID'] = "AWS_ACCESS_KEY_ID"
    # os.environ['AWS_SECRET_ACCESS_KEY'] = "AWS_SECRET_ACCESS_KEY"
    # os.environ['AWS_DEFAULT_REGION'] = "us-east-1"

    # Run the appropriate main function based on mode
    try:
        if args.mode == 'text':
            asyncio.run(main_text_only(debug=args.debug))
        elif args.mode == 'audio':
            asyncio.run(main_audio_only(debug=args.debug))
        elif args.mode == 'mixed':
            asyncio.run(main_mixed_mode(debug=args.debug))
        else:  # select mode
            asyncio.run(main_with_mode_selection(debug=args.debug))
    except Exception as e:
        print(f"Application error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
