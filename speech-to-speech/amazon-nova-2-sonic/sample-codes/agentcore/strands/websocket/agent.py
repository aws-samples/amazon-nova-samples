import logging
import traceback

from fastapi import WebSocket, WebSocketDisconnect

from strands.experimental.bidi.agent import BidiAgent
from strands.experimental.bidi.models import BidiNovaSonicModel

logger = logging.getLogger(__name__)


DEFAULT_SYSTEM_PROMPT = '''You are a friendly companion having a casual chat. Be warm, conversational, and natural. Keep responses concise and engaging.'''


def get_system_prompt() -> str:
    """Get the default system prompt for the banking assistant."""
    return DEFAULT_SYSTEM_PROMPT


async def handle_websocket_session(websocket: WebSocket, default_gateway_arns: list, send_output=None):
    """
    Handle a WebSocket session: wait for config event, initialize agent, and run.

    Args:
        websocket: The accepted WebSocket connection.
        default_gateway_arns: Gateway ARNs from environment (used as fallback).
        send_output: Optional async callable for sending output events. Defaults to websocket.send_json.
    """
    agent = None
    output_fn = send_output or websocket.send_json

    logger.info(f"Connection from {websocket.client}")
    logger.info("⏳ Waiting for config event from client...")

    try:
        # Wait for initial config event
        config = await _wait_for_config(websocket)
        if config is None:
            return

        # Initialize agent from config
        agent = _create_agent(config, default_gateway_arns)
        logger.info("✅ Agent initialized successfully")
        logger.info(f"   Config: model={config['model_id']}, region={config['region']}, voice={config['voice']}, audio={config['input_sample_rate']}Hz/{config['output_sample_rate']}Hz")

        # Send acknowledgment back to client
        await websocket.send_json({
            "type": "system",
            "message": f"Configuration applied: {config['model_id']} with voice={config['voice']}, region={config['region']}"
        })

        # Define input handler
        async def handle_websocket_input():
            """Handle incoming messages from the client, filtering config, text, and audio."""
            while True:
                message = await websocket.receive_json()

                # Handle subsequent config events (not allowed after initialization)
                if message.get("type") == "config":
                    logger.info("⚠️ Config event received after initialization - ignoring")
                    await websocket.send_json({
                        "type": "system",
                        "message": "Configuration can only be set once per session. Please reconnect to change settings."
                    })
                    continue

                # Check if it's a text message from the client
                elif message.get("type") == "text_input":
                    text = message.get("text", "")
                    logger.info(f"Received text input: {text}")
                    await agent.send(text)
                    continue

                # Audio and other events - pass through to agent
                else:
                    return message

        # Start the agent with the input handler
        await agent.run(inputs=[handle_websocket_input], outputs=[output_fn])

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        # Ignore AWS CRT cancelled future errors during cleanup
        if "InvalidStateError" in type(e).__name__ or "CANCELLED" in str(e):
            logger.warning(f"Ignoring CRT cleanup error: {e}")
        else:
            logger.error(f"Error: {e}")
            traceback.print_exc()
            try:
                await output_fn({"type": "error", "message": str(e)})
            except Exception:
                pass
    finally:
        logger.info("Connection closed")


async def _wait_for_config(websocket: WebSocket) -> dict | None:
    """Wait for the initial config event from the client. Returns parsed config or None."""
    while True:
        message = await websocket.receive_json()

        if message.get("type") == "config":
            voice = message.get("voice", "tiffany")
            input_sr = message.get("input_sample_rate", 16000)
            output_sr = message.get("output_sample_rate", 16000)
            model_id = message.get("model_id", "amazon.nova-2-sonic-v1:0")
            region = message.get("region", "us-east-1")
            gateway_arns = message.get("gateway_arns", None)
            system_prompt = message.get("system_prompt", None)

            logger.info("📥 Received config event:")
            logger.info(f"   Voice: {voice}")
            logger.info(f"   Model: {model_id}")
            logger.info(f"   Region: {region}")
            logger.info(f"   Audio: {input_sr}Hz input, {output_sr}Hz output")

            return {
                "voice": voice,
                "input_sample_rate": input_sr,
                "output_sample_rate": output_sr,
                "model_id": model_id,
                "region": region,
                "gateway_arns": gateway_arns,
                "system_prompt": system_prompt,
            }
        else:
            logger.warning(f"⚠️ Expected config event, got {message.get('type')}")
            await websocket.send_json({
                "type": "system",
                "message": "Please send config event first"
            })


def _create_agent(config: dict, default_gateway_arns: list) -> BidiAgent:
    """Create and return a BidiAgent from the given config."""
    # Use gateway ARNs from config if provided, otherwise use environment defaults
    effective_gateway_arns = config["gateway_arns"] if config["gateway_arns"] else default_gateway_arns
    effective_system_prompt = config["system_prompt"] if config["system_prompt"] else get_system_prompt()

    if config["gateway_arns"]:
        logger.info(f"   Gateways: {len(config['gateway_arns'])} from config event")
    else:
        logger.info(f"   Gateways: {len(default_gateway_arns)} from environment")

    logger.info(f"🎤 Initializing agent with model: {config['model_id']}, voice: {config['voice']}, region: {config['region']}")
    logger.info(f"📝 System prompt: {effective_system_prompt[:100]}...")

    model = BidiNovaSonicModel(
        client_config={"region": config.get("region", "us-east-1")},
        model_id=config["model_id"],
        provider_config={
            "audio": {
                "input_rate": config["input_sample_rate"],
                "output_rate": config["output_sample_rate"],
                "voice": config["voice"],
            }
        },
        mcp_gateway_arn=effective_gateway_arns,
    )

    return BidiAgent(
        model=model,
        tools=[],
        system_prompt=effective_system_prompt,
    )
