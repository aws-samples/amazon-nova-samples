#!/usr/bin/env python3
"""
FIXED VERSION - Improved Nova Sonic + Twilio integration
Key fixes:
- Better session management
- Proper initialization timing
- Improved error handling
- Fixed context frame delivery
"""

import os
import json
import asyncio
import logging
import subprocess
import signal
import sys
import time
from typing import Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, HTTPException
from fastapi.responses import Response, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv

# Pipecat imports
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.services.aws_nova_sonic.aws import AWSNovaSonicLLMService, Params
from pipecat.services.aws.llm import AWSBedrockLLMContext
from pipecat.services.llm_service import FunctionCallParams
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.transports.services.helpers.daily_rest import (
    DailyRESTHelper,
    DailyRoomParams,
)
from pipecat.frames.frames import StartFrame, EndFrame

import aiohttp
import ssl
import certifi

# Create SSL context
ssl_context = ssl.create_default_context(cafile=certifi.where())
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store active sessions
bot_procs = {}  # WebRTC bot processes
call_sessions: Dict[str, Dict[str, Any]] = {}  # Twilio call sessions
daily_helpers = {}


# Weather function for Nova Sonic
async def fetch_weather_from_api(params: FunctionCallParams):
    """Weather API function for Nova Sonic."""
    temperature = 75 if params.arguments["format"] == "fahrenheit" else 24
    await params.result_callback(
        {
            "conditions": "nice",
            "temperature": temperature,
            "format": params.arguments["format"],
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        }
    )


weather_function = FunctionSchema(
    name="get_current_weather",
    description="Get the current weather",
    properties={
        "location": {
            "type": "string",
            "description": "The city and state, e.g. San Francisco, CA",
        },
        "format": {
            "type": "string",
            "enum": ["celsius", "fahrenheit"],
            "description": "The temperature unit to use. Infer this from the users location.",
        },
    },
    required=["location", "format"],
)

tools = ToolsSchema(standard_tools=[weather_function])


async def run_twilio_bot(websocket: WebSocket, stream_sid: str, call_sid: str):
    """Run the Pipecat bot for a specific Twilio call."""
    logger.info(f"🤖 Creating Nova Sonic pipeline for call {call_sid}")

    try:
        # Create Twilio serializer
        serializer = TwilioFrameSerializer(
            stream_sid=stream_sid,
            call_sid=call_sid,
            account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
            auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        )

        # Create FastAPI WebSocket transport
        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                audio_in_sample_rate=8000,
                audio_out_sample_rate=8000,
                audio_out_channels=1,
                add_wav_header=False,
                vad_analyzer=SileroVADAnalyzer(),  #
                serializer=serializer,
                session_timeout=120,  # Increased timeout
            ),
        )

        # Improved system instruction
        system_instruction = (
            "You are a helpful AI assistant answering phone calls. "
            "Keep responses concise and natural. After answering questions, "
            "ask if there's anything else you can help with to keep the conversation going. "
            "You can provide weather information using the get_current_weather function. "
            "Always be polite and helpful."
        )

        # Create Nova Sonic service with improved configuration
        try:
            llm = AWSNovaSonicLLMService(
                access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region=os.getenv("AWS_REGION"),
                voice_id="matthew",
                system_instructions=system_instruction,
                # Add these parameters for better stability
                params=Params(
                    input_sample_rate=8000,
                    output_sample_rate=8000,
                    input_sample_size=16,
                    output_sample_size=16,
                    input_channel_count=1,
                    output_channel_count=1,
                    max_tokens=512,
                    temperature=0.7,
                    top_p=0.9,
                ),
            )

            # Wait longer for initialization and register function
            await asyncio.sleep(0.5)  # Increased wait time
            llm.register_function("get_current_weather", fetch_weather_from_api)
            logger.info(f"✅ Nova Sonic service initialized for call {call_sid}")

        except Exception as e:
            logger.error(f"Failed to initialize Nova Sonic: {e}")
            raise

        context = AWSBedrockLLMContext(
            messages=[{"role": "system", "content": system_instruction}],
            tools=tools,
        )
        context_aggregator = llm.create_context_aggregator(context)

        # Build pipeline
        pipeline = Pipeline(
            [
                transport.input(),
                context_aggregator.user(),
                llm,
                transport.output(),
                context_aggregator.assistant(),
            ]
        )

        # Create task with improved parameters
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
                audio_in_sample_rate=8000,
                audio_out_sample_rate=8000,
                send_initial_empty_metrics=False,  # Avoid initial frame issues
            ),
        )

        # Store session info
        call_sessions[call_sid].update(
            {
                "pipeline": pipeline,
                "task": task,
                "transport": transport,
                "llm": llm,
                "context_aggregator": context_aggregator,
                "nova_sonic_ready": False,
            }
        )

        # Flag to track Nova Sonic readiness
        nova_sonic_connected = asyncio.Event()
        initial_greeting_sent = False

        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            """Handle client connection - improved timing."""
            logger.info(f"🔗 Client connected for call {call_sid}")

            # Wait a bit for Nova Sonic to be fully ready
            await asyncio.sleep(1.0)

            try:
                # Mark Nova Sonic as ready
                call_sessions[call_sid]["nova_sonic_ready"] = True
                nova_sonic_connected.set()

                # Send initial context frame
                context_frame = context_aggregator.user().get_context_frame()
                await task.queue_frames([context_frame])

                # Send a greeting to start the conversation
                if not initial_greeting_sent:
                    logger.info(f"🎤 Sending initial greeting for call {call_sid}")
                    # Let Nova Sonic generate its own greeting based on system prompt

                logger.info(f"✅ Pipeline fully initialized for call {call_sid}")

            except Exception as e:
                logger.error(f"❌ Error in client connected handler: {e}")

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            """Handle client disconnection."""
            logger.info(f"🔌 Client disconnected for call {call_sid}")
            await task.cancel()

        # Additional error handling for Nova Sonic
        original_error_handler = getattr(llm, "_handle_error", None)

        def enhanced_error_handler(error):
            logger.error(f"🚨 Nova Sonic error for call {call_sid}: {error}")
            if "No open prompt found" in str(error) or "No open content found" in str(
                error
            ):
                logger.info(f"🔄 Nova Sonic session lost, will reconnect automatically")
            if original_error_handler:
                return original_error_handler(error)

        # Override error handler if possible
        if hasattr(llm, "_handle_error"):
            llm._handle_error = enhanced_error_handler

        # Start the pipeline
        logger.info(f"🚀 Starting pipeline for call {call_sid}")
        runner = PipelineRunner(handle_sigint=False)

        # Wait for Nova Sonic to be ready before running
        try:
            await asyncio.wait_for(nova_sonic_connected.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning(
                f"⚠️ Nova Sonic not ready within timeout for call {call_sid}, proceeding anyway"
            )

        await runner.run(task)

        logger.info(f"✅ Nova Sonic pipeline completed for call {call_sid}")

    except Exception as e:
        logger.error(f"❌ Error in Nova Sonic pipeline for call {call_sid}: {e}")
        import traceback

        logger.error(f"❌ Traceback: {traceback.format_exc()}")
    finally:
        await cleanup_call_session(call_sid)


def cleanup():
    """Cleanup function for graceful shutdown."""
    logger.info("Starting cleanup...")
    for pid, entry in bot_procs.items():
        proc = entry[0]
        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    logger.info("Cleanup completed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager."""
    # Initialize aiohttp session
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    aiohttp_session = aiohttp.ClientSession()

    daily_helpers["rest"] = DailyRESTHelper(
        daily_api_key=os.getenv("DAILY_API_KEY", ""),
        daily_api_url="https://api.daily.co/v1",
        aiohttp_session=aiohttp_session,
    )

    yield

    await aiohttp_session.close()
    cleanup()


# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    daily_helper = daily_helpers.get("rest")
    if not daily_helper:
        raise HTTPException(status_code=503, detail="Daily API helper not initialized")

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "fixed-nova-sonic-server",
        "webrtc_enabled": bool(os.getenv("DAILY_API_KEY")),
        "twilio_enabled": bool(os.getenv("TWILIO_AUTH_TOKEN")),
        "nova_sonic_enabled": bool(os.getenv("AWS_ACCESS_KEY_ID")),
        "phone_number": os.getenv("TWILIO_PHONE_NUMBER"),
    }


async def create_room_and_token():
    """Create Daily room and token."""
    room = await daily_helpers["rest"].create_room(DailyRoomParams())
    if not room.url:
        raise HTTPException(status_code=500, detail="Failed to create room")

    token = await daily_helpers["rest"].get_token(room.url)
    if not token:
        raise HTTPException(status_code=500, detail="Failed to get token")

    return room.url, token


@app.get("/")
async def start_webrtc_agent(request: Request):
    """Start WebRTC agent (existing functionality)."""
    logger.info("Starting WebRTC agent")
    room_url, token = await create_room_and_token()

    try:
        proc = subprocess.Popen(
            ["python3", "-m", "bot", "-u", room_url, "-t", token],
            shell=False,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        bot_procs[proc.pid] = (proc, room_url, time.time())
        logger.info(f"WebRTC bot started - PID: {proc.pid}, Room: {room_url}")

        return RedirectResponse(room_url)
    except Exception as e:
        logger.error(f"Failed to start WebRTC bot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {e}")


@app.post("/connect")
async def rtvi_connect(request: Request):
    """RTVI connect endpoint."""
    logger.info("Creating RTVI connection")
    room_url, token = await create_room_and_token()

    try:
        proc = subprocess.Popen(
            ["python3", "-m", "bot", "-u", room_url, "-t", token],
            shell=False,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        bot_procs[proc.pid] = (proc, room_url, time.time())
        logger.info(f"RTVI bot started - PID: {proc.pid}, Room: {room_url}")

        return {"room_url": room_url, "token": token}
    except Exception as e:
        logger.error(f"Failed to start RTVI bot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {e}")


@app.post("/incoming-call")
@app.get("/incoming-call")
async def handle_incoming_call(request: Request):
    """Handle incoming Twilio calls with proper TwiML."""
    logger.info("📞 Incoming Twilio call received!")

    if request.method == "GET":
        form_data = dict(request.query_params)
    else:
        form_data = await request.form()
        form_data = dict(form_data)

    caller = form_data.get("From", "Unknown")
    call_sid = form_data.get("CallSid", "Unknown")

    logger.info(f"Call from {caller}, SID: {call_sid}")

    try:
        call_sessions[call_sid] = {
            "caller": caller,
            "start_time": asyncio.get_event_loop().time(),
            "status": "connecting",
        }

        response = VoiceResponse()

        # Use <Connect><Stream> for bidirectional audio
        connect = response.connect()

        # Get WebSocket URL - Try different approaches for Twilio compatibility
        def get_websocket_url(request: Request, call_sid: str) -> str:
            """Generate proper WebSocket URL for Twilio."""
            # Use environment variable for external domain if available
            external_domain = os.getenv("EXTERNAL_DOMAIN")
            force_https = os.getenv("FORCE_HTTPS", "false").lower() == "true"
            
            if external_domain:
                # Use the configured external domain
                host = external_domain
                # Force HTTPS if configured or if we detect load balancer forwarding
                forwarded_proto = request.headers.get("x-forwarded-proto", "http")
                use_https = force_https or forwarded_proto == "https"
                ws_protocol = "wss" if use_https else "ws"
            else:
                # Fallback to header-based detection
                forwarded_proto = request.headers.get("x-forwarded-proto", "http")
                host = request.headers.get("x-forwarded-host") or request.headers.get(
                    "host", "localhost"
                )
                ws_protocol = "wss" if forwarded_proto == "https" else "ws"

            return f"{ws_protocol}://{host}/media-stream/{call_sid}"

        # Try both ws:// and wss:// - Twilio might accept ws:// for testing
        # For production, this should always be wss://
        websocket_url = get_websocket_url(request, call_sid)

        logger.info(f"🔗 Host header: {host}")
        logger.info(f"🔗 Base URL: {request.base_url}")
        logger.info(f"🔗 Generated WebSocket URL: {websocket_url}")

        # Use Connect+Stream for bidirectional audio
        connect.stream(url=websocket_url)

        logger.info(f"✅ TwiML response generated for call {call_sid}")
        logger.info(f"🔗 WebSocket URL: {websocket_url}")

        return Response(content=str(response), media_type="application/xml")

    except Exception as e:
        logger.error(f"❌ Error handling incoming call: {e}")
        error_response = VoiceResponse()
        error_response.say(
            "Sorry, there was an error. Please try again later.",
            voice="alice",
        )
        return Response(content=str(error_response), media_type="application/xml")


@app.websocket("/media-stream/{call_sid}")
async def handle_media_stream(websocket: WebSocket, call_sid: str):
    """Handle Twilio media stream with enhanced debugging."""
    await websocket.accept()
    logger.info(f"🔄 Media stream connected for call {call_sid}")

    session = call_sessions.get(call_sid)
    if not session:
        logger.error(f"❌ No session found for call {call_sid}")
        await websocket.close()
        return

    session["status"] = "streaming"

    # Simplified logging - remove the debug wrapper that might cause issues
    try:
        # Wait for connected event
        connected_message = await websocket.receive_text()
        connected_data = json.loads(connected_message)

        logger.info(
            f"📡 Received: {connected_data.get('event')} - Protocol: {connected_data.get('protocol', 'unknown')}"
        )

        if connected_data.get("event") == "connected":
            logger.info(f"📡 Twilio connected for call {call_sid}")

            # Wait for start event
            start_message = await websocket.receive_text()
            start_data = json.loads(start_message)

            logger.info(f"🎤 Received: {start_data.get('event')} event")

            if start_data.get("event") == "start":
                stream_sid = start_data.get("start", {}).get("streamSid")
                media_format = start_data.get("start", {}).get("mediaFormat", {})

                logger.info(f"🎤 Audio streaming started:")
                logger.info(f"   - Call ID: {call_sid}")
                logger.info(f"   - Stream ID: {stream_sid}")
                logger.info(f"   - Media format: {media_format}")

                session["stream_sid"] = stream_sid

                # Start the Nova Sonic bot
                await run_twilio_bot(websocket, stream_sid, call_sid)
            else:
                logger.error(
                    f"❌ Expected 'start' event, got: {start_data.get('event')}"
                )
                await websocket.close()
        else:
            logger.error(
                f"❌ Expected 'connected' event, got: {connected_data.get('event')}"
            )
            await websocket.close()

    except Exception as e:
        logger.error(f"❌ WebSocket error for call {call_sid}: {e}")
        import traceback

        logger.error(f"❌ Traceback: {traceback.format_exc()}")
    finally:
        logger.info(f"🔌 Media stream disconnected for call {call_sid}")
        await cleanup_call_session(call_sid)


async def cleanup_call_session(call_sid: str):
    """Clean up call session."""
    session = call_sessions.get(call_sid)
    if not session:
        return

    try:
        if "task" in session:
            await session["task"].cancel()

        session["status"] = "ended"
        session["end_time"] = asyncio.get_event_loop().time()
        duration = session.get("end_time", 0) - session.get("start_time", 0)
        logger.info(f"📊 Call {call_sid} ended - Duration: {duration:.1f}s")
    except Exception as e:
        logger.error(f"❌ Error cleaning up call session {call_sid}: {e}")


@app.get("/active-calls")
async def get_active_calls():
    """Get active call sessions."""
    active_calls = []
    current_time = asyncio.get_event_loop().time()

    for call_sid, session in call_sessions.items():
        if session.get("status") in ["connecting", "streaming"]:
            duration = current_time - session.get("start_time", current_time)
            active_calls.append(
                {
                    "call_sid": call_sid,
                    "status": session.get("status"),
                    "caller": session.get("caller"),
                    "duration": duration,
                    "has_pipeline": "pipeline" in session,
                    "nova_sonic_ready": session.get("nova_sonic_ready", False),
                }
            )

    return {
        "active_calls": active_calls,
        "total_active": len(active_calls),
        "webrtc_bots": len([p for p in bot_procs.values() if p[0].poll() is None]),
    }


if __name__ == "__main__":
    import uvicorn
    import argparse

    # Set up signal handlers
    signal.signal(signal.SIGTERM, lambda s, f: (cleanup(), sys.exit(0)))
    signal.signal(signal.SIGINT, lambda s, f: (cleanup(), sys.exit(0)))

    default_host = os.getenv("HOST", "0.0.0.0")
    default_port = int(os.getenv("FAST_API_PORT", "7860"))

    parser = argparse.ArgumentParser(description="Fixed Nova Sonic + Twilio server")
    parser.add_argument("--host", type=str, default=default_host, help="Host address")
    parser.add_argument("--port", type=int, default=default_port, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Reload on change")

    config = parser.parse_args()

    logger.info(f"🚀 Starting Fixed Nova Sonic server on {config.host}:{config.port}")
    logger.info(f"📞 Twilio phone: {os.getenv('TWILIO_PHONE_NUMBER')}")
    logger.info(f"🌐 WebRTC: {bool(os.getenv('DAILY_API_KEY'))}")
    logger.info(f"🤖 Nova Sonic: {bool(os.getenv('AWS_ACCESS_KEY_ID'))}")

    try:
        uvicorn.run(
            "server_clean:app",
            host=config.host,
            port=config.port,
            reload=config.reload,
            access_log=True,
            log_level="info",
        )
    except KeyboardInterrupt:
        logger.info("Server stopped")
        cleanup()
    except Exception as e:
        logger.error(f"Server error: {e}")
        cleanup()
        sys.exit(1)
