"""Tool processing for async execution."""
import asyncio
import json
import uuid
from typing import Dict, Any
from src.core.utils import debug_print
from src.agents.tools import open_ticket_tool, order_computers_tool, check_order_location_tool


class ToolProcessor:
    """Handles asynchronous tool execution."""
    
    def __init__(self):
        self.tasks = {}
        self._tool_map = {
            'open_ticket_tool': open_ticket_tool,
            'order_computers_tool': order_computers_tool,
            'check_order_location_tool': check_order_location_tool
        }
    
    async def process_tool_async(self, tool_name: str, tool_content: Dict[str, Any]) -> Dict[str, Any]:
        """Process tool call asynchronously."""
        task_id = str(uuid.uuid4())
        task = asyncio.create_task(self._run_tool(tool_name, tool_content))
        self.tasks[task_id] = task
        
        try:
            return await task
        finally:
            self.tasks.pop(task_id, None)
    
    async def _run_tool(self, tool_name: str, tool_content: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool logic."""
        debug_print(f"Processing tool: {tool_name}")
        
        tool_func = self._tool_map.get(tool_name.lower())
        if not tool_func:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            content = tool_content.get("content", {})
            params = json.loads(content) if isinstance(content, str) else content
            return await tool_func(**params)
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}
