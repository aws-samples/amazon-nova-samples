import asyncio
import json
import base64
import warnings
import uuid
from s2s_events import S2sEvent
import time
from aws_sdk_bedrock_runtime.client import BedrockRuntimeClient, InvokeModelWithBidirectionalStreamOperationInput
from aws_sdk_bedrock_runtime.models import InvokeModelWithBidirectionalStreamInputChunk, BidirectionalInputPayloadPart
from aws_sdk_bedrock_runtime.config import Config, HTTPAuthSchemeResolver, SigV4AuthScheme
from smithy_aws_core.credentials_resolvers.environment import EnvironmentCredentialsResolver
from integration import inline_agent, bedrock_knowledge_bases as kb, agent_core

# load environment variables from .env file
from dotenv import load_dotenv
import os
load_dotenv() 

# AgentCore Observability integration
from opentelemetry import baggage, context, trace

# Suppress warnings
warnings.filterwarnings("ignore")

DEBUG = True

def debug_print(message):
    """Print only if debug mode is enabled"""
    if DEBUG:
        print(message)


class S2sSessionManager:
    """Manages bidirectional streaming with AWS Bedrock using asyncio"""
    
    def __init__(self, region, model_id='amazon.nova-sonic-v1:0', mcp_client=None, strands_agent=None):
        """Initialize the stream manager."""
        self.model_id = model_id
        self.region = region
        
        # Audio and output queues
        self.audio_input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        
        self.response_task = None
        self.stream = None
        self.is_active = False
        self.bedrock_client = None
        
        # Session information
        self.prompt_name = None  # Will be set from frontend
        self.content_name = None  # Will be set from frontend
        self.audio_content_name = None  # Will be set from frontend
        self.toolUseContent = ""
        self.toolUseId = ""
        self.toolName = ""
        self.mcp_loc_client = mcp_client
        self.strands_agent = strands_agent

        # Track content generation stages by contentId
        self.content_stages = {}  # Maps contentId to generationStage

        # Usage event tracking
        self.usage_events = []
        self.token_usage = {
            "totalInputTokens": 0,
            "totalOutputTokens": 0,
            "totalTokens": 0,
            "details": {
                "input": {
                    "speechTokens": 0,
                    "textTokens": 0
                },
                "output": {
                    "speechTokens": 0,
                    "textTokens": 0
                }
            }
        }
        
        # Telemetry
        self.session_id = str(uuid.uuid4())  # Unique session ID
        self.session_span = None
        self._create_session_span()
    
    def _calculate_cost(self, token_usage):
        """
        Calculate the cost based on token usage and Nova Sonic pricing.
        
        Args:
            token_usage: Dictionary containing token usage information
            
        Returns:
            Total cost in USD
        """
        # Nova Sonic pricing information (USD per 1000 tokens)
        NOVA_SONIC_PRICING = {
            "speech_input": 0.0034,  # $0.0034 per 1000 speech input tokens
            "speech_output": 0.0136,  # $0.0136 per 1000 speech output tokens
            "text_input": 0.00006,    # $0.00006 per 1000 text input tokens
            "text_output": 0.00024    # $0.00024 per 1000 text output tokens
        }
        if not token_usage:
            return 0.0
        
        speech_input_tokens = token_usage.get('input', {}).get('speechTokens', 0)
        text_input_tokens = token_usage.get('input', {}).get('textTokens', 0)
        speech_output_tokens = token_usage.get('output', {}).get('speechTokens', 0)
        text_output_tokens = token_usage.get('output', {}).get('textTokens', 0)
        
        # Calculate cost components (convert from price per 1000 tokens)
        speech_input_cost = (speech_input_tokens / 1000) * NOVA_SONIC_PRICING["speech_input"]
        text_input_cost = (text_input_tokens / 1000) * NOVA_SONIC_PRICING["text_input"]
        speech_output_cost = (speech_output_tokens / 1000) * NOVA_SONIC_PRICING["speech_output"]
        text_output_cost = (text_output_tokens / 1000) * NOVA_SONIC_PRICING["text_output"]
        
        # Calculate total cost
        total_cost = speech_input_cost + text_input_cost + speech_output_cost + text_output_cost
        debug_print(f"Calculated cost: {total_cost:.6f} USD for session {self.session_id}")
        return total_cost
    
    def _create_session_span(self):
        """Create the session span for telemetry when the session manager is initialized"""
        if not self.session_id:
            # Generate a session ID if not provided
            self.session_id = str(uuid.uuid4())
        
        # Create a session span (this implicitly creates a trace)
        trace_name = f"{self.session_id}"
        
        # Set session context for telemetry
        context_token = self.set_session_context(self.session_id)
        debug_print(f"Session context set with token: {context_token}")

        # Get tracer for main application
        try:
            tracer = trace.get_tracer("s2s_agent", "1.0.0")
            # Create the session span
            self.session_span = tracer.start_span(trace_name)
            if hasattr(self.session_span, 'set_attribute'):
                self.session_span.set_attribute("session.id", self.session_id)
                self.session_span.set_attribute("model.id", self.model_id)
                self.session_span.set_attribute("region", self.region)
            
        except Exception as telemetry_error:
            raise


    def set_session_context(self, session_id):
        """Set the session ID in OpenTelemetry baggage for trace correlation"""
        ctx = baggage.set_baggage("session.id", session_id)
        token = context.attach(ctx)

        return token
        

    def _create_child_span(self, name, input=None, parent_span=None, metadata=None, output=None):
        """Create a child span for telemetry using OpenTelemetry"""
            
        try:
            debug_print(f"Creating child span: {name}")
            # Get a tracer for the agent
            tracer = trace.get_tracer("s2s_agent", "1.0.0")
            
            # Start a new span as a child of the parent span if provided
            # If no parent span is provided, it will be a child of the current active span
            span_context = None
            if parent_span and isinstance(parent_span, trace.Span):
                # If we have a parent span, use its context
                debug_print("Using provided parent span for child span")
                span_context = trace.set_span_in_context(parent_span)
            
            # Create the span with the provided name
            span = tracer.start_span(name, context=span_context)
            
            # Add standard attributes
            if hasattr(span, 'set_attribute'):
                span.set_attribute("session.id", self.session_id)
                
                # Add input data if provided
                if input:
                    self._add_attributes_to_span(span, input, "input")
                
                # Add metadata if provided
                if metadata:
                    self._add_attributes_to_span(span, metadata, "")
                
                # Add output data if provided
                if output:
                    self._add_attributes_to_span(span, output, "output")
                
                # Add start time event
                span.add_event("span_started")
            return span
        except Exception as e:
            raise

    def _add_attributes_to_span(self, span, data, prefix=""):
        """
        Recursively add attributes to a span from complex data structures.
        
        Args:
            span: The OpenTelemetry span to add attributes to
            data: The data to add (can be dict, list, or primitive)
            prefix: The attribute name prefix
        """
        if not hasattr(span, 'set_attribute'):
            return
            
        def _flatten_and_add(obj, current_prefix=""):
            """Recursively flatten nested objects and add as span attributes"""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_prefix = f"{current_prefix}.{key}" if current_prefix else key
                    if isinstance(value, (dict, list)):
                        # For complex nested objects, serialize to JSON string
                        try:
                            json_str = json.dumps(value)
                            # Truncate very long JSON strings
                            if len(json_str) > 1000:
                                json_str = json_str[:997] + "..."
                            span.set_attribute(new_prefix, json_str)
                        except (TypeError, ValueError):
                            # If JSON serialization fails, convert to string
                            str_value = str(value)
                            if len(str_value) > 1000:
                                str_value = str_value[:997] + "..."
                            span.set_attribute(new_prefix, str_value)
                    elif isinstance(value, (str, int, float, bool, type(None))):
                        # Handle primitive types directly
                        if value is None:
                            span.set_attribute(new_prefix, "null")
                        else:
                            str_value = str(value)
                            # Truncate very long strings
                            if len(str_value) > 1000:
                                str_value = str_value[:997] + "..."
                            span.set_attribute(new_prefix, str_value)
                    else:
                        # For other types, convert to string
                        str_value = str(value)
                        if len(str_value) > 1000:
                            str_value = str_value[:997] + "..."
                        span.set_attribute(new_prefix, str_value)
            elif isinstance(obj, list):
                # For lists, serialize to JSON string
                try:
                    json_str = json.dumps(obj)
                    if len(json_str) > 1000:
                        json_str = json_str[:997] + "..."
                    span.set_attribute(current_prefix or "list", json_str)
                except (TypeError, ValueError):
                    str_value = str(obj)
                    if len(str_value) > 1000:
                        str_value = str_value[:997] + "..."
                    span.set_attribute(current_prefix or "list", str_value)
            else:
                # For primitive types or other objects
                if obj is None:
                    span.set_attribute(current_prefix or "value", "null")
                else:
                    str_value = str(obj)
                    if len(str_value) > 1000:
                        str_value = str_value[:997] + "..."
                    span.set_attribute(current_prefix or "value", str_value)
        
        try:
            _flatten_and_add(data, prefix)
        except Exception as e:

            # Fallback: add as simple string
            try:
                fallback_value = str(data)
                if len(fallback_value) > 1000:
                    fallback_value = fallback_value[:997] + "..."
                span.set_attribute(prefix or "data", fallback_value)
            except Exception as fallback_error:
                raise


    def _end_span_safely(self, span, output=None, level="INFO", status_message=None, end_time=None, metadata=None):
        """End a span safely with additional attributes using OpenTelemetry"""
        try:
            if not span:
                return
            
            # Add output data if provided
            if output and hasattr(span, 'set_attribute'):
                self._add_attributes_to_span(span, output, "output")
            
            # Add additional metadata if provided
            if metadata and hasattr(span, 'set_attribute'):
                self._add_attributes_to_span(span, metadata, "")
            
            # Set span status based on level
            if hasattr(span, 'set_status'):
                if level == "ERROR":
                    error_message = status_message or "An error occurred"
                    span.set_status(trace.Status(trace.StatusCode.ERROR, error_message))
                    if hasattr(span, 'add_event'):
                        span.add_event("error", {"message": error_message})
                else:
                    span.set_status(trace.Status(trace.StatusCode.OK))
            
            # Add end time event
            if hasattr(span, 'add_event'):
                span.add_event("span_ended")
            
            # End the span
            span.end()
            
        except Exception as e:
            raise

    def _initialize_client(self):
        """Initialize the Bedrock client."""
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
            http_auth_scheme_resolver=HTTPAuthSchemeResolver(),
            http_auth_schemes={"aws.auth#sigv4": SigV4AuthScheme()}
        )
        self.bedrock_client = BedrockRuntimeClient(config=config)

    async def initialize_stream(self):
        """Initialize the bidirectional stream with Bedrock."""
        try:
            if not self.bedrock_client:
                self._initialize_client()
        except Exception as ex:
            self.is_active = False
            print(f"Failed to initialize Bedrock client: {str(e)}")
            raise

        try:
            # Initialize the stream
            self.stream = await self.bedrock_client.invoke_model_with_bidirectional_stream(
                InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
            )
            self.is_active = True
            
            # Start listening for responses
            self.response_task = asyncio.create_task(self._process_responses())

            # Start processing audio input
            asyncio.create_task(self._process_audio_input())
            
            # Wait a bit to ensure everything is set up
            await asyncio.sleep(0.1)
            
            debug_print("Stream initialized successfully")
            return self
        except Exception as e:
            self.is_active = False
            print(f"Failed to initialize stream: {str(e)}")
            raise
    
    async def send_raw_event(self, event_data):
        try:
            """Send a raw event to the Bedrock stream."""
            if not self.stream or not self.is_active:
                debug_print("Stream not initialized or closed")
                return
            
            event_json = json.dumps(event_data)
            
            event_span = None

            if "event" in event_data:
                event_type = list(event_data["event"].keys())[0]
                
                # Create event-specific spans as children of session span
                if event_type == "sessionStart":
                    debug_print("Creating sessionStart span")
                    event_span = self._create_child_span(
                        "sessionStart",
                        parent_span=self.session_span,
                        input=event_data["event"]["sessionStart"],
                        metadata={
                            "session_id": self.session_id,
                            
                            }
                    )
                    
                    
                elif event_type == "sessionEnd":
                    debug_print("Creating sessionEnd span")
                    event_span = self._create_child_span(
                        "sessionEnd",
                        parent_span=self.session_span,
                        input=event_data["event"]["sessionEnd"],
                        metadata={
                            "session_id": self.session_id
                        }
                    )
                    

                elif event_type == "promptStart":
                    debug_print
                    event_span = self._create_child_span(
                        "promptStart",
                        parent_span=self.session_span,
                        input=event_data["event"]["promptStart"],
                        metadata={
                            "session_id": self.session_id,
                            "prompt_name": event_data["event"]["promptStart"].get("promptName"),
                            "content_name": event_data["event"]["promptStart"].get("contentName"),
                            # "audio_output_configuration": event_data["event"]["promptStart"].get("audioOutputConfiguration"),
                            # "tool_configuration": event_data["event"]["promptStart"].get("toolConfiguration"),
                        }
                    )
                       
                    
                elif event_type == "textInput":
                    debug_print("Creating textInput span")
                    text_input_data = event_data["event"]["textInput"]
                    if text_input_data.get("content"):
                        event_span = self._create_child_span(
                            "systemPrompt",
                            parent_span= self.session_span,
                            input=text_input_data.get("content"),
                            metadata={
                                "session_id": self.session_id,
                                "prompt_name": text_input_data.get("promptName"),
                                "content_name": text_input_data.get("contentName"),
                            }
                        )
                        


            event = InvokeModelWithBidirectionalStreamInputChunk(
                value=BidirectionalInputPayloadPart(bytes_=event_json.encode('utf-8'))
            )
            await self.stream.input_stream.send(event)

            # Update event span with success
            if event_span:
                debug_print(f"Ending event span for {event_type}")
                self._end_span_safely(event_span, 
                    output={"status": "sent", "event_type": event_type if "event" in event_data else "unknown"}
                )

            # Close session
            if "sessionEnd" in event_data["event"]:
                self.close()
            
        except Exception as e:
            debug_print(f"Error sending event: {str(e)}")
    
    async def _process_audio_input(self):
        """Process audio input from the queue and send to Bedrock."""
        while self.is_active:
            try:
                debug_print("Waiting for audio data...")
                # Get audio data from the queue
                data = await self.audio_input_queue.get()
                
                # Extract data from the queue item
                prompt_name = data.get('prompt_name')
                content_name = data.get('content_name')
                audio_bytes = data.get('audio_bytes')
                
                if not audio_bytes or not prompt_name or not content_name:
                    debug_print("Missing required audio data properties")
                    continue

                # Create the audio input event
                audio_event = S2sEvent.audio_input(prompt_name, content_name, audio_bytes.decode('utf-8') if isinstance(audio_bytes, bytes) else audio_bytes)
                
                debug_print(f"Sending audio chunk for prompt: {prompt_name}, content: {content_name}")

                # Send the event
                await self.send_raw_event(audio_event)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                debug_print(f"Error processing audio: {e}")
                if DEBUG:
                    import traceback
                    traceback.print_exc()
    
    def add_audio_chunk(self, prompt_name, content_name, audio_data):
        """Add an audio chunk to the queue."""
        # The audio_data is already a base64 string from the frontend
        self.audio_input_queue.put_nowait({
            'prompt_name': prompt_name,
            'content_name': content_name,
            'audio_bytes': audio_data
        })
    
    async def _process_responses(self):
        """Process incoming responses from Bedrock."""
        while self.is_active:
            try:            
                output = await self.stream.await_output()
                result = await output[1].receive()
                
                if result.value and result.value.bytes_:
                    response_data = result.value.bytes_.decode('utf-8')
                    
                    json_data = json.loads(response_data)
                    json_data["timestamp"] = int(time.time() * 1000)  # Milliseconds since epoch
                    
                    event_name = None
                    if 'event' in json_data:
                        event_name = list(json_data["event"].keys())[0]
                       
                        # Handle usage events
                        if event_name == 'usageEvent':
                            # logger.info("Received usage event")
                            # Store the usage event
                            event_data = json_data['event']['usageEvent']
                            self.usage_events.append(event_data)
                            
                            # Update token usage aggregates
                            if 'totalInputTokens' in event_data:
                                self.token_usage['totalInputTokens'] = event_data.get('totalInputTokens', 0)
                            if 'totalOutputTokens' in event_data:
                                self.token_usage['totalOutputTokens'] = event_data.get('totalOutputTokens', 0)
                            if 'totalTokens' in event_data:
                                self.token_usage['totalTokens'] = event_data.get('totalTokens', 0)
                            
                            # Update detailed token usage if available
                            if 'details' in event_data:
                                details = event_data.get('details', {})
                                if 'delta' in details:
                                    delta = details.get('delta', {})
                                    # Update input tokens
                                    if 'input' in delta:
                                        input_delta = delta.get('input', {})
                                        self.token_usage['details']['input']['speechTokens'] += input_delta.get('speechTokens', 0)
                                        self.token_usage['details']['input']['textTokens'] += input_delta.get('textTokens', 0)
                                    # Update output tokens
                                    if 'output' in delta:
                                        output_delta = delta.get('output', {})
                                        self.token_usage['details']['output']['speechTokens'] += output_delta.get('speechTokens', 0)
                                        self.token_usage['details']['output']['textTokens'] += output_delta.get('textTokens', 0)
                                
                                # If total values are provided, use those instead
                                if 'total' in details:
                                    total = details.get('total', {})
                                    if 'input' in total:
                                        input_total = total.get('input', {})
                                        self.token_usage['details']['input']['speechTokens'] = input_total.get('speechTokens', 
                                            self.token_usage['details']['input']['speechTokens'])
                                        self.token_usage['details']['input']['textTokens'] = input_total.get('textTokens', 
                                            self.token_usage['details']['input']['textTokens'])
                                    if 'output' in total:
                                        output_total = total.get('output', {})
                                        self.token_usage['details']['output']['speechTokens'] = output_total.get('speechTokens', 
                                            self.token_usage['details']['output']['speechTokens'])
                                        self.token_usage['details']['output']['textTokens'] = output_total.get('textTokens', 
                                            self.token_usage['details']['output']['textTokens'])
                            

                            if self.session_span:
                                cost = self._calculate_cost(self.token_usage['details'])

                                if hasattr(self.session_span, 'set_attribute'):
                                    self.session_span.set_attribute("input_tokens", self.token_usage['totalInputTokens'])
                                    self.session_span.set_attribute("output_tokens", self.token_usage['totalOutputTokens'])
                                    self.session_span.set_attribute("total_tokens", self.token_usage['totalTokens'])
                                    self.session_span.set_attribute("cost", cost)
                                    self.session_span.set_attribute("currency", "USD")
                                    # Add an event for token usage update
                                    self.session_span.add_event("token_usage_updated", {
                                        "input_tokens": self.token_usage['totalInputTokens'],
                                        "output_tokens": self.token_usage['totalOutputTokens'],
                                        "total_tokens": self.token_usage['totalTokens'],
                                        "cost": cost
                                    })
                        
                        if event_name == 'textOutput':
                            prompt_name = json_data['event'].get('textOutput', {}).get("promptName")
                            content = json_data['event'].get('textOutput', {}).get("content")
                            content_id = json_data['event'].get('textOutput', {}).get("contentId")
                            role = json_data['event'].get('textOutput', {}).get("role", "ASSISTANT")
                            #lowercase the role and append "user" with "Input" and "assistant" with "Output"
                            if role == "USER":
                                messageType = "userInput"
                            elif role == "ASSISTANT":
                                messageType = "assistantOutput"
                            
                            # Only create a span if this is a FINAL generation (not SPECULATIVE)
                            generation_stage = self.content_stages.get(content_id, "FINAL")
                            
                            if generation_stage == "FINAL":
                                debug_print(f"Creating {messageType} span for textOutput")
                                response_span = self._create_child_span(
                                    messageType,
                                    parent_span=self.session_span,
                                    metadata={
                                        "session_id": self.session_id,
                                        "prompt_name": prompt_name,
                                        "generation_stage": "FINAL"},
                                    output={"content": content}
                                )
                                
                                self._end_span_safely(response_span)


                        
                        # Handle tool use detection
                        if event_name == 'toolUse':
                            self.toolUseContent = json_data['event']['toolUse']
                            self.toolName = json_data['event']['toolUse']['toolName']
                            self.toolUseId = json_data['event']['toolUse']['toolUseId']
                            debug_print(f"Tool use detected: {self.toolName}, ID: {self.toolUseId}, "+ json.dumps(json_data['event']))

                        # Process tool use when content ends
                        elif event_name == 'contentEnd' and json_data['event'][event_name].get('type') == 'TOOL':
                            prompt_name = json_data['event']['contentEnd'].get("promptName")
                            debug_print("Processing tool use and sending result")
                            toolResult = await self.processToolUse(self.toolName, self.toolUseContent)
                                
                            # Send tool start event
                            toolContent = str(uuid.uuid4())
                            tool_start_event = S2sEvent.content_start_tool(prompt_name, toolContent, self.toolUseId)
                            await self.send_raw_event(tool_start_event)
                            
                            # Send tool result event
                            if isinstance(toolResult, dict):
                                content_json_string = json.dumps(toolResult)
                            else:
                                content_json_string = toolResult

                            tool_result_event = S2sEvent.text_input_tool(prompt_name, toolContent, content_json_string)
                            print("Tool result", tool_result_event)
                            await self.send_raw_event(tool_result_event)

                            # Send tool content end event
                            tool_content_end_event = S2sEvent.content_end(prompt_name, toolContent)
                            await self.send_raw_event(tool_content_end_event)
                    
                    # Put the response in the output queue for forwarding to the frontend
                    await self.output_queue.put(json_data)


            except json.JSONDecodeError as ex:
                print(ex)
                await self.output_queue.put({"raw_data": response_data})
            except StopAsyncIteration as ex:
                # Stream has ended
                print(ex)
            except Exception as e:
                # Handle ValidationException properly
                if "ValidationException" in str(e):
                    error_message = str(e)
                    print(f"Validation error: {error_message}")
                else:
                    print(f"Error receiving response: {e}")
                break

        self.is_active = False
        self.close()

    async def processToolUse(self, toolName, toolUseContent):
        """Return the tool result"""
        print(f"Tool Use Content: {toolUseContent}")

        toolName = toolName.lower()
        content, result = None, None
        try:

            # Call the tool function with unpacked parameters
            tool_start_time = time.time_ns()            

            # Create tool use span as a child of the current prompt or session span
            response_span = self._create_child_span(
                "toolUse",
                parent_span=self.session_span,
                input={
                    "toolName": toolName,
                    "params": toolUseContent.get("content")
                },
                metadata={
                    "session_id": self.session_id,
                    "tool_start_time": tool_start_time,
                }
            )

            if toolUseContent.get("content"):
                # Parse the JSON string in the content field
                query_json = json.loads(toolUseContent.get("content"))
                content = toolUseContent.get("content")  # Pass the JSON string directly to the agent
                print(f"Extracted query: {content}")
            
            # AgentCore integration
            if toolName.startswith("ac_"):
                result = agent_core.invoke_agent_core(toolName, content)

            # Simple toolUse to get system time in UTC
            if toolName == "getdatetool":
                from datetime import datetime, timezone
                result = datetime.now(timezone.utc).strftime('%A, %Y-%m-%d %H-%M-%S')

            # Bedrock Knowledge Bases (RAG)
            if toolName == "getkbtool":
                result = kb.retrieve_kb(content)

            # MCP integration - location search                        
            if toolName == "getlocationtool":
                if self.mcp_loc_client:
                    result = await self.mcp_loc_client.call_tool(content)
            
            # Strands Agent integration - weather questions
            if toolName == "externalagent":
                if self.strands_agent:
                    result = self.strands_agent.query(content)

            # Bedrock Agents integration - Bookings
            if toolName == "getbookingdetails":
                try:
                    # Pass the tool use content (JSON string) directly to the agent
                    result = await inline_agent.invoke_agent(content)
                    # Try to parse and format if needed
                    try:
                        booking_json = json.loads(result)
                        if "bookings" in booking_json:
                            result = await inline_agent.invoke_agent(
                                f"Format this booking information for the user: {result}"
                            )
                    except Exception:
                        pass  # Not JSON, just return as is
                    
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {str(e)}")
                    return {"result": f"Invalid JSON format for booking details: {str(e)}"}
                except Exception as e:
                    print(f"Error processing booking details: {str(e)}")
                    return {"result": f"Error processing booking details: {str(e)}"}

            if not result:
                result = "no result found"
            
            tool_end_time = time.time_ns()
            tool_run_time = tool_end_time - tool_start_time
            
            self._end_span_safely(response_span,
                    output={"result": result},
                    end_time=tool_end_time,
                    metadata={"tool_run_time": tool_run_time, "tool_start_time": tool_start_time, "tool_end_time": tool_end_time},
                )
            
            return {"result": result}
        except Exception as ex:
            print(ex)
            return {"result": "An error occurred while attempting to retrieve information related to the toolUse event."}
    
    async def close(self):
        """Close the stream properly."""
        if not self.is_active:
            return
            
        self.is_active = False
        
        if self.stream:
            await self.stream.input_stream.close()
        
        if self.response_task and not self.response_task.done():
            self.response_task.cancel()
            try:
                await self.response_task
            except asyncio.CancelledError:
                pass
