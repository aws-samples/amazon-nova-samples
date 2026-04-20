"""
AFTER: Voice agent migrated from the OpenAI function-calling text agent.

Migration steps applied:
1. Extracted SYSTEM_PROMPT and TOOLS from text_agent.py
2. Rewrote system prompt for voice (see diff below)
3. Converted OpenAI function schemas to MCP Tool schemas (voice_tools_mcp.py)
4. Replaced OpenAI chat.completions with BidiAgent + BidiNovaSonicModel
"""

import logging
from fastapi import WebSocket, WebSocketDisconnect
from strands.experimental.bidi.agent import BidiAgent
from strands.experimental.bidi.models.nova_sonic import BidiNovaSonicModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Voice-optimized system prompt
#
# Original (from text_agent.py):
#   "You are a technical support specialist for CloudCorp.
#    Help users troubleshoot issues with their cloud infrastructure.
#    When diagnosing problems, always check the service status first.
#    Provide step-by-step solutions with exact CLI commands.
#    Format responses in markdown with code blocks for commands.
#    Include error codes in your responses for reference."
#
# Changes:
#   - Removed "markdown", "code blocks", "error codes in responses"
#   - Added greeting, brevity, spoken-language instructions
#   - Added confirmation before destructive actions (restart)
#   - Kept the diagnostic flow (check status first)
# ---------------------------------------------------------------------------

VOICE_SYSTEM_PROMPT = """You are a friendly technical support specialist for CloudCorp.
You're on a voice call helping a customer troubleshoot their cloud infrastructure.

Start with: "Hi there! This is CloudCorp support. What seems to be the issue?"

When diagnosing problems, check the service status first, then look at error logs
if needed. Walk the customer through what you find in plain language.

Keep each response to one or two sentences. Don't read out error codes, log entries,
or command-line syntax — summarize what you found instead.
For example, say "It looks like your database service has been having connection
timeouts for the last hour" instead of reading raw log entries.

Before restarting any service, confirm with the customer:
"I'd recommend restarting your [service] instance. This will cause about thirty
seconds of downtime. Should I go ahead?"

Use acknowledgments while checking things: "Let me take a look at that."

If you can't resolve the issue: "I'd recommend opening a support ticket for this.
Would you like me to help with anything else?"

End calls with: "Glad I could help! Don't hesitate to call back if anything else
comes up."\""""


async def handle_websocket_session(websocket: WebSocket, default_gateway_arns: list):
    """Handle a voice support session — migrated from OpenAI function-calling agent."""
    try:
        config = await websocket.receive_json()
        if config.get("type") != "config":
            await websocket.send_json({"type": "system", "message": "Send config event first"})
            return

        gateway_arns = config.get("gateway_arns") or default_gateway_arns

        model = BidiNovaSonicModel(
            region=config.get("region", "us-east-1"),
            model_id=config.get("model_id", "amazon.nova-2-sonic-v1:0"),
            provider_config={
                "audio": {
                    "input_sample_rate": config.get("input_sample_rate", 16000),
                    "output_sample_rate": config.get("output_sample_rate", 16000),
                    "voice": config.get("voice", "tiffany"),
                }
            },
            mcp_gateway_arn=gateway_arns,
        )

        agent = BidiAgent(
            model=model,
            tools=[],
            system_prompt=config.get("system_prompt") or VOICE_SYSTEM_PROMPT,
        )

        await websocket.send_json({
            "type": "system",
            "message": "Voice support agent ready"
        })

        async def handle_input():
            while True:
                message = await websocket.receive_json()
                if message.get("type") == "text_input":
                    await agent.send(message.get("text", ""))
                    continue
                return message

        await agent.run(inputs=[handle_input], outputs=[websocket.send_json])

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Session error: {e}")
