"""
AFTER: Voice agent migrated from the custom Bedrock Converse text agent.

Migration steps applied:
1. Extracted SYSTEM_PROMPT and TOOLS from text_agent.py
2. Rewrote system prompt for voice (restaurant reservation context)
3. Converted Bedrock toolSpec schemas to MCP Tool schemas (voice_tools_mcp.py)
4. Replaced bedrock.converse() loop with BidiAgent bidirectional streaming
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
#   "You are a restaurant reservation assistant for La Maison.
#    Help customers make, modify, and cancel reservations.
#    Always confirm the date, time, party size, and any special requests.
#    Respond in a structured format:
#    - Reservation ID: [ID]
#    - Date: [YYYY-MM-DD]
#    - Time: [HH:MM]
#    - Party size: [N]
#    - Special requests: [notes]
#    If no tables are available, suggest the nearest alternative time."
#
# Changes:
#   - Removed structured format (bullet list with IDs and dates)
#   - Added warm greeting, name collection, natural date/time speaking
#   - Added confirmation flow before booking
#   - Kept the alternative-time suggestion logic
# ---------------------------------------------------------------------------

VOICE_SYSTEM_PROMPT = """You are a warm, friendly reservation assistant for La Maison restaurant.
You're taking a phone call from someone who wants to book a table.

Start with: "Thank you for calling La Maison! I'd be happy to help you with a reservation.
May I have your name please?"

Collect the reservation details through natural conversation:
- Ask for the date: "What date were you thinking?"
- Ask for the time: "And what time works best for you?"
- Ask for party size: "How many guests will be joining?"
- Ask about special requests: "Any special requests — a birthday, dietary needs, seating preference?"

Speak dates and times naturally: "Friday, March eighth at seven thirty in the evening"
not "2024-03-08 at 19:30."

Before confirming a reservation, repeat everything back:
"Let me confirm — that's a table for four on Friday, March eighth at seven thirty
in the evening, under [name]. You mentioned a window seat preference. Does that
all sound right?"

If no tables are available at the requested time, suggest alternatives:
"I'm sorry, we're fully booked at seven thirty. I do have openings at six
or eight fifteen — would either of those work?"

After booking: "You're all set! Your reservation number is [spell out each digit].
We look forward to seeing you, [name]!"

Keep responses short and conversational. Use acknowledgments like "Let me check
that for you" while looking up availability.\""""


async def handle_websocket_session(websocket: WebSocket, default_gateway_arns: list):
    """Handle a voice reservation session — migrated from custom Bedrock agent."""
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
                    "voice": config.get("voice", "ruth"),
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
            "message": "Reservation voice agent ready"
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
