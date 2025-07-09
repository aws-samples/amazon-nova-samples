import asyncio
import json
import warnings
import uuid
import time
import traceback
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from aws_sdk_bedrock_runtime.client import (
    BedrockRuntimeClient,
    InvokeModelWithBidirectionalStreamOperationInput,
)
from aws_sdk_bedrock_runtime.models import (
    InvokeModelWithBidirectionalStreamInputChunk,
    BidirectionalInputPayloadPart,
)
from aws_sdk_bedrock_runtime.config import (
    Config,
    HTTPAuthSchemeResolver,
    SigV4AuthScheme,
)
from smithy_aws_core.credentials_resolvers.environment import (
    EnvironmentCredentialsResolver,
)
from smithy_core.aio.eventstream import DuplexEventStream

from sonic_events import SonicEvent
from integration import inline_agent, bedrock_knowledge_bases as kb

# Suppress warnings
warnings.filterwarnings("ignore")

DEBUG = False


def debug_print(message):
    """Print only if debug mode is enabled"""
    if DEBUG:
        print(message)


class SessionManager:
    """Manages bidirectional streaming with AWS Bedrock using asyncio"""

    forward_task: asyncio.Task
    stream: DuplexEventStream
    bedrock_client: BedrockRuntimeClient

    def __init__(
        self,
        websocket: WebSocket,
        region,
        model_id="amazon.nova-sonic-v1:0",
        mcp_client=None,
        strands_agent=None,
        kb_id=None,
    ):
        """Initialize the stream manager."""
        self.websocket = websocket
        self.model_id = model_id
        self.region = region

        # Audio and output queues
        self.audio_input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()

        self.response_task = None
        self.is_active = False

        # Session information
        self.prompt_name = None  # Will be set from frontend
        self.content_name = None  # Will be set from frontend
        self.audio_content_name = None  # Will be set from frontend
        self.toolUseContent = ""
        self.toolUseId = ""
        self.toolName = ""
        self.mcp_loc_client = mcp_client
        self.strands_agent = strands_agent
        self.kb_id = kb_id
        self.public_ip_address = None
        self.geolocation_position = None

        self.location_data_available = asyncio.Event()

    def _initialize_client(self):
        """Initialize the Bedrock client."""
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
            http_auth_scheme_resolver=HTTPAuthSchemeResolver(),
            http_auth_schemes={"aws.auth#sigv4": SigV4AuthScheme()},
        )
        self.bedrock_client = BedrockRuntimeClient(config=config)

    async def initialize_stream(self):
        """Initialize the bidirectional stream with Bedrock."""
        try:
            self._initialize_client()
        except Exception as e:
            self.is_active = False
            print(f"Failed to initialize Bedrock client: {e}")
            raise

        self.forward_task = asyncio.create_task(self.forward_responses_from_bedrock_to_frontend())

        try:
            # Initialize the stream
            self.stream = (
                await self.bedrock_client.invoke_model_with_bidirectional_stream(
                    InvokeModelWithBidirectionalStreamOperationInput(
                        model_id=self.model_id
                    )
                )
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
            print(f"Failed to initialize stream: {e}")
            raise

    async def forward_responses_from_bedrock_to_frontend(self):
        """Forward responses from Bedrock to the frontend via the websocket connection."""
        try:
            while True:
                # Get next response from the output queue
                response = await self.output_queue.get()

                try:
                    event = json.dumps(response)
                    await self.websocket.send_text(event)
                except WebSocketDisconnect:
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error forwarding responses: {e}")


    async def handle_incoming_message_from_frontend(self, message: str):
        data = json.loads(message)
        if 'body' in data:
            data = json.loads(data["body"])
        if 'event' not in data:
            debug_print(f"unknown event: {data}")
            return

        event_name = list(data['event'].keys())[0]

        if "audioInput" not in data.get("event", {}).keys():
            debug_print(f"event message: {data}")
        if "APP_CUSTOM_state_update" in data.get("event", {}).keys():
            print(f"Received custom app state update: {data}")
            payload = data["event"]["APP_CUSTOM_state_update"]
            self.update_app_state(payload)
            return

        # Store prompt name and content names if provided
        if event_name == 'promptStart':
            self.prompt_name = data['event']['promptStart']['promptName']
        elif event_name == 'contentStart' and data['event']['contentStart'].get('type') == 'AUDIO':
            self.audio_content_name = data['event']['contentStart']['contentName']

        # Handle audio input separately
        if event_name == 'audioInput':
            # Extract audio data
            prompt_name = data['event']['audioInput']['promptName']
            content_name = data['event']['audioInput']['contentName']
            audio_base64 = data['event']['audioInput']['content']

            # Add to the audio queue
            self.add_audio_chunk(prompt_name, content_name, audio_base64)
        else:
            # Send other events directly to Bedrock
            await self.send_raw_event(data)


    async def send_raw_event(self, event_data):
        try:
            """Send a raw event to the Bedrock stream."""
            if not self.stream or not self.is_active:
                debug_print("Stream not initialized or closed")
                return

            event_json = json.dumps(event_data)
            event = InvokeModelWithBidirectionalStreamInputChunk(
                value=BidirectionalInputPayloadPart(bytes_=event_json.encode("utf-8"))
            )
            await self.stream.input_stream.send(event)

            # Close session
            if "sessionEnd" in event_data["event"]:
                await self.close()

        except Exception as e:
            debug_print(f"Error sending event: {e}")

    async def _process_audio_input(self):
        """Process audio input from the queue and send to Bedrock."""
        while self.is_active:
            try:
                # Get audio data from the queue
                data = await self.audio_input_queue.get()

                # Extract data from the queue item
                prompt_name = data.get("prompt_name")
                content_name = data.get("content_name")
                audio_bytes = data.get("audio_bytes")

                if not audio_bytes or not prompt_name or not content_name:
                    debug_print("Missing required audio data properties")
                    continue

                # Create the audio input event
                audio_event = SonicEvent.audio_input(
                    prompt_name,
                    content_name,
                    (
                        audio_bytes.decode("utf-8")
                        if isinstance(audio_bytes, bytes)
                        else audio_bytes
                    ),
                )

                # Send the event
                await self.send_raw_event(audio_event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                debug_print(f"Error processing audio: {e}")
                if DEBUG:
                    traceback.print_exc()

    def add_audio_chunk(self, prompt_name, content_name, audio_data):
        """Add an audio chunk to the queue."""
        # The audio_data is already a base64 string from the frontend
        self.audio_input_queue.put_nowait(
            {
                "prompt_name": prompt_name,
                "content_name": content_name,
                "audio_bytes": audio_data,
            }
        )

    def update_app_state(self, data):
        public_ip_address = data.get("publicIpAddress", None)
        if public_ip_address:
            self.public_ip_address = public_ip_address
            print(f"App state updated: {public_ip_address=}")

        geolocation_position = data.get("geolocationPosition", None)
        if geolocation_position:
            self.geolocation_position = geolocation_position
            self.location_data_available.set()
            print(f"App state updated: {geolocation_position=}")

    async def _process_responses(self):
        """Process incoming responses from Bedrock."""
        while self.is_active:
            response_data = None
            try:
                output = await self.stream.await_output()
                result = await output[1].receive()

                if result.value and result.value.bytes_:
                    response_data = result.value.bytes_.decode("utf-8")

                    json_data = json.loads(response_data)
                    json_data["timestamp"] = int(
                        time.time() * 1000
                    )  # Milliseconds since epoch

                    # Put the response in the output queue for forwarding to the frontend
                    await self.output_queue.put(json_data)
                    await asyncio.sleep(0) # yield to allow the event to be sent to the frontend before processing it further

                    event_name = None
                    if "event" in json_data:
                        event_name = list(json_data["event"].keys())[0]

                        # Handle tool use detection
                        if event_name == "toolUse":
                            self.toolUseContent = json_data["event"]["toolUse"]
                            self.toolName = json_data["event"]["toolUse"]["toolName"]
                            self.toolUseId = json_data["event"]["toolUse"]["toolUseId"]
                            debug_print(
                                f"Tool use detected: {self.toolName}, ID: {self.toolUseId}, "
                                + json.dumps(json_data["event"])
                            )

                        # Process tool use when content ends
                        elif (
                            event_name == "contentEnd"
                            and json_data["event"][event_name].get("type") == "TOOL"
                        ):
                            prompt_name = json_data["event"]["contentEnd"].get("promptName")

                            # Send tool start event
                            toolContent = str(uuid.uuid4())
                            tool_start_event = SonicEvent.content_start_tool(
                                prompt_name, toolContent, self.toolUseId
                            )
                            await self.send_raw_event(tool_start_event)

                            debug_print("Processing tool use and sending result")
                            toolResult = await self.process_tool_use(self.toolName, self.toolUseContent)

                            # Send tool result event
                            if isinstance(toolResult, dict):
                                content_json_string = json.dumps(toolResult)
                            else:
                                content_json_string = toolResult

                            tool_result_event = SonicEvent.text_input_tool(
                                prompt_name, toolContent, content_json_string
                            )
                            print("Tool result", tool_result_event)
                            await self.send_raw_event(tool_result_event)

                            # make the toolResult visible in the frontend as well
                            tool_result_event["timestamp"] = int(datetime.now().timestamp() * 1000)
                            tool_result_event["event"]["toolResult"]["content"] = toolResult
                            await self.output_queue.put(tool_result_event)

                            # Send tool content end event
                            tool_content_end_event = SonicEvent.content_end(
                                prompt_name, toolContent
                            )
                            await self.send_raw_event(tool_content_end_event)


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
        await self.close()

    async def process_tool_use(self, toolName, toolUseContent):
        """Return the tool result"""
        print(f"Tool Use Content: {toolUseContent}")

        toolName = toolName.lower()
        content, result = None, None
        try:
            content = toolUseContent.get("content", None)
            print(f"Extracted query: {content}")

            # Simple toolUse to get system time in UTC
            if toolName == "getdatetool":
                result = datetime.now().strftime("%A, %Y-%m-%d %H-%M-%S local time")

            # browser / frontend integration to retrieve data via side channel
            if toolName == "locateme":
                print(f"locateMe: {content}")
                await asyncio.wait_for(self.location_data_available.wait(), 15.0)

                if self.public_ip_address or self.geolocation_position:
                    result = {
                        "public_ip_address": self.public_ip_address,
                        "geolocation_position": self.geolocation_position
                    }
                else:
                    result = "No position information available yet."
                print(f"locateMe result: {result}")

            # Bedrock Knowledge Bases (RAG)
            if toolName == "getkbtool":
                result = kb.retrieve_kb(self.kb_id, content)

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
                    return {
                        "result": f"Invalid JSON format for booking details: {str(e)}"
                    }
                except Exception as e:
                    print(f"Error processing booking details: {str(e)}")
                    return {"result": f"Error processing booking details: {str(e)}"}

            if not result:
                result = "no result found"

            return {"result": result}
        except Exception as ex:
            print("Error in processToolUse:", ex)
            return {
                "result": "An error occurred while attempting to retrieve information related to the toolUse event."
            }

    async def close(self):
        """Close all resources properly."""
        if not self.is_active:
            return

        self.is_active = False

        if self.stream:
            await self.stream.input_stream.close()

        if self.response_task:
            self.response_task.cancel()

        if self.forward_task:
            self.forward_task.cancel()
