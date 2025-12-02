import asyncio
import json
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class McpLocationClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.stdio: Optional[Any] = None
        self.write: Optional[Any] = None

    async def connect_to_server(self):
        aws_profile = os.getenv("AWS_PROFILE")
        env = {"FASTMCP_LOG_LEVEL": "ERROR"}
        if aws_profile:
            env["AWS_PROFILE"] = aws_profile
            
        server_params = StdioServerParameters(
                command="uvx",
                args=["awslabs.aws-location-mcp-server@latest"],
                env=env
            )
        
        # Connect to the server
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        # Initialize the connection
        await self.session.initialize()

    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        tools_result = await self.session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools_result.tools
        ]

    async def call_tool(self, input):
        if isinstance(input, str):
            input = json.loads(input)
        
        tool_name = input.get("tool", "search_places")
        query = input.get("query", input)

        response = await self.session.call_tool(tool_name, {"query":query})
        print("!!!!",tool_name, query, response)
        result = []
        for c in response.content:
            result.append(c.text)
        return result

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()
