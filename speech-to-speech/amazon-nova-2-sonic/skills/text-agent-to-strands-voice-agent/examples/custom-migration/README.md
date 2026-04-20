# Custom Agent (Bedrock Converse) Text-to-Voice Migration Example

Migrates a hand-rolled Bedrock Converse agent with `toolSpec` definitions to a Strands BidiAgent voice agent. Demonstrates a restaurant reservation use case.

## Files

| File | Role |
|------|------|
| `text_agent.py` | **BEFORE** — Custom agent using `boto3 bedrock.converse()` with toolSpec tools |
| `voice_agent.py` | **AFTER** — Migrated voice session handler with voice-optimized prompt |
| `voice_tools_mcp.py` | **AFTER** — Bedrock toolSpec schemas converted to MCP Tool definitions |

## What Changed

1. **System prompt**: Removed structured format (bullet list with IDs/dates), added warm greeting, natural date/time speaking, confirmation flow before booking
2. **Tools**: Bedrock `toolSpec.inputSchema.json` unwrapped to MCP `Tool.inputSchema` — one level of nesting removed, logic unchanged
3. **Agent**: Replaced `bedrock.converse()` request/response loop with `BidiAgent.run()` bidirectional streaming
4. **Transport**: Synchronous boto3 calls → async WebSocket audio streaming

## Schema Conversion Note

Bedrock Converse nests the JSON schema one level deeper than MCP:

```
Bedrock:  toolSpec.inputSchema.json.properties...
MCP:      Tool.inputSchema.properties...
```

Just unwrap the `.json` key when converting.
