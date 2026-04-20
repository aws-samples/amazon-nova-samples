"""
MCP server wrapping the original OpenAI function-calling tools for voice.

The OpenAI function schemas from text_agent.py TOOLS are converted to
MCP Tool definitions. The tool logic is identical.

Run standalone: python voice_tools_mcp.py
"""

import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("support-tools")


# ---------------------------------------------------------------------------
# Tool functions — same logic as text_agent.py
# ---------------------------------------------------------------------------

def check_service_status(service_name: str) -> dict:
    return {"service": service_name, "status": "degraded", "uptime": "99.2%", "incidents": 1}


def get_error_logs(service_name: str, hours: int = 1) -> dict:
    return {"service": service_name, "errors": [
        {"time": "14:32", "code": "E5012", "msg": "Connection timeout to primary replica"},
        {"time": "14:35", "code": "E5012", "msg": "Connection timeout to primary replica"},
    ]}


def restart_service(service_name: str, instance_id: str) -> dict:
    return {"status": "restarting", "service": service_name, "instance": instance_id, "eta": "30s"}


# ---------------------------------------------------------------------------
# MCP Tool definitions — converted from OpenAI function schemas
#
# OpenAI format:
#   {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}
#
# MCP format:
#   Tool(name=..., description=..., inputSchema={...})
#
# The inputSchema is identical to OpenAI's "parameters" field.
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="check_service_status",
        description="Check the current status of a cloud service",
        inputSchema={
            "type": "object",
            "properties": {
                "service_name": {"type": "string", "description": "Name of the service"}
            },
            "required": ["service_name"],
        },
    ),
    Tool(
        name="get_error_logs",
        description="Retrieve recent error logs for a service",
        inputSchema={
            "type": "object",
            "properties": {
                "service_name": {"type": "string", "description": "Service name"},
                "hours": {"type": "integer", "description": "Hours of logs to retrieve", "default": 1},
            },
            "required": ["service_name"],
        },
    ),
    Tool(
        name="restart_service",
        description="Restart a cloud service instance",
        inputSchema={
            "type": "object",
            "properties": {
                "service_name": {"type": "string", "description": "Service to restart"},
                "instance_id": {"type": "string", "description": "Instance ID"},
            },
            "required": ["service_name", "instance_id"],
        },
    ),
]

TOOL_FUNCTIONS = {
    "check_service_status": lambda **kw: check_service_status(**kw),
    "get_error_logs": lambda **kw: get_error_logs(**kw),
    "restart_service": lambda **kw: restart_service(**kw),
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
