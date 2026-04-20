# OpenAI Function-Calling Text-to-Voice Migration Example

Migrates a raw OpenAI `chat.completions` agent with function calling to a Strands BidiAgent voice agent.

## Files

| File | Role |
|------|------|
| `text_agent.py` | **BEFORE** — OpenAI text agent with `tools=[{"type":"function",...}]` |
| `voice_agent.py` | **AFTER** — Migrated voice session handler with voice-optimized prompt |
| `voice_tools_mcp.py` | **AFTER** — OpenAI function schemas converted to MCP Tool definitions |

## What Changed

1. **System prompt**: Removed markdown/code-block instructions, added spoken-language flow, confirmation before restarts
2. **Tools**: OpenAI `"parameters"` schema maps directly to MCP `inputSchema` — same structure, different wrapper
3. **Agent**: Replaced `client.chat.completions.create()` loop with `BidiAgent.run()` bidirectional streaming
4. **Transport**: HTTP request/response → WebSocket bidirectional audio
