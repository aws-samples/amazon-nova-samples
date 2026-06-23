"""Unit tests for ToolRegistry.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
"""

import sys
import os
import json

import pytest
from typing import Dict, Any

from src.agents.tool_registry import ToolRegistry, SWITCH_AGENT_SCHEMA
from src.agents.agent_config import Agent, ToolDefinition


# --- Helpers ---

async def dummy_tool(x: str) -> Dict[str, Any]:
    return {"result": x}


async def failing_tool(x: str) -> Dict[str, Any]:
    raise RuntimeError("boom")


def make_agent(name: str, tools: list) -> Agent:
    return Agent(voice_id="v1", instruction="test", tools=tools)


def make_tool_def(name: str, callable=dummy_tool) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=f"Desc for {name}",
        input_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        callable=callable,
    )


# --- from_agents tests ---

class TestFromAgents:
    def test_builds_registry_from_agents(self):
        agents = {
            "support": make_agent("support", [make_tool_def("tool_a")]),
            "sales": make_agent("sales", [make_tool_def("tool_b")]),
        }
        registry = ToolRegistry.from_agents(agents)

        assert "tool_a" in registry._tools
        assert "tool_b" in registry._tools
        assert registry._agent_tool_names["support"] == ["tool_a"]
        assert registry._agent_tool_names["sales"] == ["tool_b"]

    def test_empty_agents(self):
        registry = ToolRegistry.from_agents({})
        assert registry._tools == {}
        assert registry._agent_tool_names == {}

    def test_agent_with_no_tools(self):
        agents = {"support": make_agent("support", [])}
        registry = ToolRegistry.from_agents(agents)
        assert registry._agent_tool_names["support"] == []

    def test_duplicate_tool_across_agents_registered_once(self):
        shared = make_tool_def("shared_tool")
        agents = {
            "a": make_agent("a", [shared]),
            "b": make_agent("b", [shared]),
        }
        registry = ToolRegistry.from_agents(agents)
        assert len(registry._tools) == 1
        assert "shared_tool" in registry._tools


# --- register tests ---

class TestRegister:
    def test_register_and_lookup(self):
        registry = ToolRegistry()
        registry.register("my_tool", dummy_tool, {"description": "d", "input_schema": {}})
        assert "my_tool" in registry._tools
        assert registry._tools["my_tool"].callable is dummy_tool


# --- get_schemas_for_agent tests ---

class TestGetSchemasForAgent:
    def test_always_includes_switch_agent(self):
        registry = ToolRegistry.from_agents({
            "support": make_agent("support", [make_tool_def("tool_a")]),
        })
        agents = {"support": make_agent("support", [make_tool_def("tool_a")])}
        schemas = registry.get_schemas_for_agent("support", agents)

        names = [s["toolSpec"]["name"] for s in schemas]
        assert "switch_agent" in names

    def test_includes_agent_specific_tools(self):
        agents = {
            "support": make_agent("support", [make_tool_def("tool_a")]),
            "sales": make_agent("sales", [make_tool_def("tool_b")]),
        }
        registry = ToolRegistry.from_agents(agents)

        support_schemas = registry.get_schemas_for_agent("support", agents)
        support_names = [s["toolSpec"]["name"] for s in support_schemas]
        assert "tool_a" in support_names
        assert "tool_b" not in support_names

        sales_schemas = registry.get_schemas_for_agent("sales", agents)
        sales_names = [s["toolSpec"]["name"] for s in sales_schemas]
        assert "tool_b" in sales_names
        assert "tool_a" not in sales_names

    def test_bedrock_compatible_format(self):
        agents = {"support": make_agent("support", [make_tool_def("tool_a")])}
        registry = ToolRegistry.from_agents(agents)
        schemas = registry.get_schemas_for_agent("support", agents)

        # Find the agent tool (not switch_agent)
        tool_schema = [s for s in schemas if s["toolSpec"]["name"] == "tool_a"][0]
        spec = tool_schema["toolSpec"]
        assert "name" in spec
        assert "description" in spec
        assert "inputSchema" in spec
        assert "json" in spec["inputSchema"]
        # inputSchema.json should be a JSON string
        parsed = json.loads(spec["inputSchema"]["json"])
        assert parsed["type"] == "object"

    def test_unknown_agent_returns_only_switch_agent(self):
        registry = ToolRegistry.from_agents({})
        schemas = registry.get_schemas_for_agent("nonexistent", {})
        assert len(schemas) == 1
        assert schemas[0]["toolSpec"]["name"] == "switch_agent"


# --- execute tests ---

class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_known_tool(self):
        registry = ToolRegistry()
        registry.register("my_tool", dummy_tool, {"description": "d", "input_schema": {}})
        result = await registry.execute("my_tool", {"x": "hello"})
        assert result == {"result": "hello"}

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        registry = ToolRegistry()
        result = await registry.execute("no_such_tool", {})
        assert "error" in result
        assert "Unknown tool: no_such_tool" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_with_string_content(self):
        registry = ToolRegistry()
        registry.register("my_tool", dummy_tool, {"description": "d", "input_schema": {}})
        result = await registry.execute("my_tool", {"content": '{"x": "from_string"}'})
        assert result == {"result": "from_string"}

    @pytest.mark.asyncio
    async def test_execute_with_dict_content(self):
        registry = ToolRegistry()
        registry.register("my_tool", dummy_tool, {"description": "d", "input_schema": {}})
        result = await registry.execute("my_tool", {"content": {"x": "from_dict"}})
        assert result == {"result": "from_dict"}

    @pytest.mark.asyncio
    async def test_execute_failure_returns_error(self):
        registry = ToolRegistry()
        registry.register("bad_tool", failing_tool, {"description": "d", "input_schema": {}})
        result = await registry.execute("bad_tool", {"x": "hello"})
        assert "error" in result
        assert "Tool execution failed: boom" in result["error"]
