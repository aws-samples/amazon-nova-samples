"""
AFTER: Voice agent migrated from the LangChain text agent.

This file shows the complete migration:
1. System prompt rewritten for voice (from text_agent.py SYSTEM_PROMPT)
2. Tools wrapped as MCP server (see voice_tools_mcp.py)
3. BidiAgent session handler using Strands

Run with: python voice_server.py
"""

import logging
from fastapi import WebSocket, WebSocketDisconnect
from strands.experimental.bidi.agent import BidiAgent
from strands.experimental.bidi.models.nova_sonic import BidiNovaSonicModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Step 1: Voice-optimized system prompt
#
# Original (from text_agent.py):
#   "You are a customer service assistant for AnyBank.
#    Help users with account balance inquiries, recent transactions,
#    and fund transfers. Always authenticate the user first.
#    Respond with structured data when available.
#    Format currency as USD with two decimal places.
#    If an error occurs, return the error code and description."
#
# Changes applied:
#   - Removed "structured data" and "USD with two decimal places"
#   - Added greeting flow, name usage, brevity, number spelling
#   - Added confirmation before transfers
#   - Added filler phrases and error handling in natural language
# ---------------------------------------------------------------------------

VOICE_SYSTEM_PROMPT = """You are a friendly, conversational customer service assistant for AnyBank.
You're having a natural phone conversation with a customer.

Start every call with: "Hello! Welcome to AnyBank. May I have your name please?"

Once you have their name, use it naturally throughout the conversation.

Before accessing any account information, verify their identity:
"Thanks, [name]. For security, could you please provide your account number
and date of birth?"

After verification: "Great, you're all set! How can I help you today?"

You can help with checking balances, recent transactions, and transfers
between accounts.

Keep responses short — one to two sentences at a time.
When sharing dollar amounts, say them naturally: "four thousand two hundred
thirty-one dollars and fifty-six cents."
When sharing dates, say them naturally: "March fourth" not "oh three oh four."

Before making any transfer, confirm the details:
"Just to confirm — you'd like to transfer [amount] from [source] to
[destination]. Is that correct?"

Use brief acknowledgments while looking things up: "Let me check that for you."

If something goes wrong: "I'm sorry, I wasn't able to do that.
Would you like to try again, or can I help with something else?"
Never mention error codes or technical details.

After helping, ask: "Is there anything else I can help with?"
End calls warmly: "Thanks for calling AnyBank, [name]. Have a great day!\""""


async def handle_websocket_session(websocket: WebSocket, default_gateway_arns: list):
    """Handle a single voice session — migrated from LangChain text agent."""
    try:
        # Wait for config from client
        config = await websocket.receive_json()
        if config.get("type") != "config":
            await websocket.send_json({"type": "system", "message": "Send config event first"})
            return

        # Step 2: Use gateway ARNs pointing to the MCP-wrapped tools
        # (see voice_tools_mcp.py for the MCP server wrapping the original @tool functions)
        gateway_arns = config.get("gateway_arns") or default_gateway_arns

        # Step 3: Create BidiAgent with voice-optimized prompt
        model = BidiNovaSonicModel(
            region=config.get("region", "us-east-1"),
            model_id=config.get("model_id", "amazon.nova-2-sonic-v1:0"),
            provider_config={
                "audio": {
                    "input_sample_rate": config.get("input_sample_rate", 16000),
                    "output_sample_rate": config.get("output_sample_rate", 16000),
                    "voice": config.get("voice", "matthew"),
                }
            },
            mcp_gateway_arn=gateway_arns,
        )

        agent = BidiAgent(
            model=model,
            tools=[],  # Tools come via MCP Gateway, not inline
            system_prompt=config.get("system_prompt") or VOICE_SYSTEM_PROMPT,
        )

        await websocket.send_json({
            "type": "system",
            "message": f"Voice agent ready — model={config.get('model_id')}, voice={config.get('voice')}"
        })

        # Input handler — routes text and audio from client to agent
        async def handle_input():
            while True:
                message = await websocket.receive_json()
                if message.get("type") == "text_input":
                    await agent.send(message.get("text", ""))
                    continue
                return message  # audio frame

        await agent.run(inputs=[handle_input], outputs=[websocket.send_json])

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Session error: {e}")
