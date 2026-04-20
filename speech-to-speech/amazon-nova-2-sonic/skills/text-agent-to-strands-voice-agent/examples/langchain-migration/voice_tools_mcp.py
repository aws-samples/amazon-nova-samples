"""
MCP server wrapping the original LangChain @tool functions for voice.

The tool logic is identical to text_agent.py — only the wrapper changes.
Deploy this behind an AgentCore MCP Gateway, then pass the gateway ARN
to the voice agent's mcp_gateway_arn.

Run standalone: python voice_tools_mcp.py
"""

import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("banking-tools")


# ---------------------------------------------------------------------------
# Tool functions — copied directly from text_agent.py @tool functions.
# The logic is unchanged; only the MCP wrapper is new.
# ---------------------------------------------------------------------------

def get_account_balance(account_id: str) -> dict:
    return {"status": "success", "account_id": account_id, "balance": 4231.56}


def get_recent_transactions(account_id: str, count: int = 5) -> dict:
    return {
        "transactions": [
            {"desc": "Coffee Shop", "amount": -4.50},
            {"desc": "Grocery Store", "amount": -62.30},
            {"desc": "Direct Deposit", "amount": 3200.00},
        ][:count]
    }


def transfer_funds(from_account: str, to_account: str, amount: float) -> dict:
    return {
        "status": "success",
        "from": from_account,
        "to": to_account,
        "amount": amount,
    }


# ---------------------------------------------------------------------------
# MCP Tool definitions — schema extracted from the @tool signatures
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="get_account_balance",
        description="Get the balance for a customer account",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "The account ID to check"}
            },
            "required": ["account_id"],
        },
    ),
    Tool(
        name="get_recent_transactions",
        description="Get recent transactions for a customer account",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "The account ID"},
                "count": {"type": "integer", "description": "Number of transactions", "default": 5},
            },
            "required": ["account_id"],
        },
    ),
    Tool(
        name="transfer_funds",
        description="Transfer funds between two accounts",
        inputSchema={
            "type": "object",
            "properties": {
                "from_account": {"type": "string", "description": "Source account ID"},
                "to_account": {"type": "string", "description": "Destination account ID"},
                "amount": {"type": "number", "description": "Amount to transfer"},
            },
            "required": ["from_account", "to_account", "amount"],
        },
    ),
]

TOOL_FUNCTIONS = {
    "get_account_balance": lambda **kw: get_account_balance(**kw),
    "get_recent_transactions": lambda **kw: get_recent_transactions(**kw),
    "transfer_funds": lambda **kw: transfer_funds(**kw),
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        raise ValueError(f"Unknown tool: {name}")
    result = func(**arguments)
    return [TextContent(type="text", text=json.dumps(result))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
