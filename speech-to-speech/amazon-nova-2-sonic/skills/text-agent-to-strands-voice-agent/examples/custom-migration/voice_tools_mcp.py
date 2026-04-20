"""
MCP server wrapping the original Bedrock Converse toolSpec functions for voice.

The Bedrock toolSpec format nests the schema under "inputSchema.json".
MCP Tool uses "inputSchema" directly — just unwrap one level.

Run standalone: python voice_tools_mcp.py
"""

import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("reservation-tools")


# ---------------------------------------------------------------------------
# Tool functions — same logic as text_agent.py
# ---------------------------------------------------------------------------

def check_availability(date: str, time: str, party_size: int) -> dict:
    return {"available": True, "tables": [{"id": "T12", "seats": 4}, {"id": "T15", "seats": 6}]}


def make_reservation(date: str, time: str, party_size: int, customer_name: str,
                     special_requests: str = "") -> dict:
    return {"reservation_id": "RES-20240304-001", "date": date, "time": time,
            "party_size": party_size, "customer_name": customer_name,
            "special_requests": special_requests, "status": "confirmed"}


def cancel_reservation(reservation_id: str) -> dict:
    return {"reservation_id": reservation_id, "status": "cancelled"}


# ---------------------------------------------------------------------------
# MCP Tool definitions — converted from Bedrock toolSpec format
#
# Bedrock format:
#   {"toolSpec": {"name": ..., "description": ..., "inputSchema": {"json": {...}}}}
#
# MCP format:
#   Tool(name=..., description=..., inputSchema={...})
#
# The conversion: unwrap "inputSchema.json" → "inputSchema"
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="check_availability",
        description="Check table availability for a given date, time, and party size",
        inputSchema={
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date (e.g., 2024-03-08)"},
                "time": {"type": "string", "description": "Time (e.g., 19:30)"},
                "party_size": {"type": "integer", "description": "Number of guests"},
            },
            "required": ["date", "time", "party_size"],
        },
    ),
    Tool(
        name="make_reservation",
        description="Create a new restaurant reservation",
        inputSchema={
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "time": {"type": "string"},
                "party_size": {"type": "integer"},
                "customer_name": {"type": "string", "description": "Guest name"},
                "special_requests": {"type": "string", "default": ""},
            },
            "required": ["date", "time", "party_size", "customer_name"],
        },
    ),
    Tool(
        name="cancel_reservation",
        description="Cancel an existing reservation by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "reservation_id": {"type": "string", "description": "The reservation ID"},
            },
            "required": ["reservation_id"],
        },
    ),
]

TOOL_FUNCTIONS = {
    "check_availability": lambda **kw: check_availability(**kw),
    "make_reservation": lambda **kw: make_reservation(**kw),
    "cancel_reservation": lambda **kw: cancel_reservation(**kw),
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
