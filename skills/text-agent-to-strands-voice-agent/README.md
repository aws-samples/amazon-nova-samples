# Text Agent to Nova Sonic Voice Agent with Strands BidiAgent — Skill

An [Agent Skill](https://agentskills.io/specification) that guides the migration of any text-based agent into a real-time voice agent using [Strands BidiAgent](https://github.com/strands-agents/sdk-python) with [Amazon Nova 2 Sonic](https://aws.amazon.com/ai/generative-ai/nova/sonic/). Strands BidiAgent provides bidirectional audio streaming — it takes your existing system prompt and `@tool` functions and runs them as a live speech-to-speech agent over WebSocket.

## What It Covers

The skill is organized into two parts:

| Part | What It Covers |
|------|---------------|
| **Frontend** | Browser WebSocket client with Web Audio API mic capture (16kHz PCM), audio playback, text input fallback, config event with system prompt |
| **Orchestrator** | FastAPI + Strands BidiAgent + BidiNovaSonicModel server, voice prompt optimization rules (brevity, number spelling, confirmations, no structured output), tool integration via `@tool` decorators or MCP Gateway |

Additional content:
- System dependency callouts (`aws_sdk_bedrock_runtime`, `pyaudio`, `portaudio`)
- Voice prompt rewriting guide with complete before/after examples
- Three migration examples (LangChain, OpenAI function-calling, custom Bedrock Converse)

## Skill Structure

```
skills/text-agent-to-strands-voice-agent/
├── SKILL.md                              # Main skill — 2-part migration guide
├── README.md                             # This file
├── references/
│   ├── voice-prompt-guide.md             # Detailed prompt rewriting reference
│   ├── server-reference.md               # Production server details (splitting, observability)
│   └── client-reference.md               # Audio capture/playback, Python CLI, event handling
└── examples/
    ├── langchain-migration/              # LangChain create_react_agent → BidiAgent
    │   ├── text_agent.py                 # BEFORE
    │   ├── voice_agent.py                # AFTER
    │   └── README.md
    ├── openai-migration/                 # OpenAI function-calling → BidiAgent
    │   ├── text_agent.py
    │   ├── voice_agent.py
    │   └── README.md
    └── custom-migration/                 # Bedrock Converse toolSpec → BidiAgent
        ├── text_agent.py
        ├── voice_agent.py
        └── README.md
```

## How to Use

### In Kiro

The skill is registered as a Kiro steering file. To set it up:

**1. Register the steering file (one command):**

```bash
mkdir -p .kiro/steering && cat > .kiro/steering/text-to-voice-migration.md << 'EOF'
---
inclusion: manual
---

# Text Agent to Nova Sonic Voice Agent Migration

When the user asks to migrate a text agent to voice, convert a chatbot to a Nova Sonic voice agent, follow the skill instructions in `#[[file:skills/text-agent-to-strands-voice-agent/SKILL.md]]`.

The skill is structured in two parts:

1. **Frontend** — Browser WebSocket client with mic capture and audio playback
2. **Orchestrator** — FastAPI + Strands BidiAgent + Nova Sonic server

## Reference Files

Load these on demand when deeper detail is needed:

- Voice prompt rewriting: `#[[file:skills/text-agent-to-strands-voice-agent/references/voice-prompt-guide.md]]`
- Server implementation details: `#[[file:skills/text-agent-to-strands-voice-agent/references/server-reference.md]]`
- Client implementation details: `#[[file:skills/text-agent-to-strands-voice-agent/references/client-reference.md]]`

## Examples

Use these as reference implementations when migrating from specific frameworks:

- LangChain migration: `#[[file:skills/text-agent-to-strands-voice-agent/examples/langchain-migration/README.md]]`
- OpenAI migration: `#[[file:skills/text-agent-to-strands-voice-agent/examples/openai-migration/README.md]]`
- Custom/Bedrock migration: `#[[file:skills/text-agent-to-strands-voice-agent/examples/custom-migration/README.md]]`

## Production Reference

The working production implementation is in the same repo:

- Server: `#[[file:speech-to-speech/amazon-nova-2-sonic/sample-codes/agentcore/strands/websocket/agent.py]]` and `#[[file:speech-to-speech/amazon-nova-2-sonic/sample-codes/agentcore/strands/websocket/server.py]]`
- Client: `#[[file:speech-to-speech/amazon-nova-2-sonic/sample-codes/agentcore/strands/client/client.py]]` and `#[[file:speech-to-speech/amazon-nova-2-sonic/sample-codes/agentcore/strands/client/strands-client.html]]`
- MCP tools: `#[[file:speech-to-speech/amazon-nova-2-sonic/sample-codes/agentcore/strands/mcp/banking_mcp.py]]`
EOF
```

This creates the directory and file in one shot. Key points:
- `inclusion: manual` means it's opt-in — type `#` in Kiro chat and select `text-to-voice-migration` to activate
- The `#[[file:...]]` syntax tells Kiro to pull in referenced file content when the steering is activated
- Change `manual` to `auto` if you want it loaded into every conversation automatically

**2. Use it in Kiro chat:**

1. In the Kiro chat input, type `#` and select `text-to-voice-migration`
2. Describe your text agent and ask to migrate it, for example:
   - "I have a text agent with this system prompt and these tools. Migrate it to a Nova Sonic voice agent."
   - "Help me convert my LangChain chatbot to voice."
3. Kiro loads the SKILL.md and follows the two-part structure, pulling in reference files as needed

**3. Sample prompt:**

```
#text-to-voice-migration generate a voice agent under a voice-agent folder using
this text agent: https://github.com/strands-agents/samples/blob/main/python/04-industry-use-cases/finance/personal-finance-assistant/lab3-multi-agent-orchestration.ipynb
```

This tells Kiro to activate the migration skill, fetch the text agent source, extract the system prompt and tools, rewrite the prompt for voice, and generate the complete voice agent (server, agent, tools, client, README) under `voice-agent/`.

### In Claude Code

```bash
# Register the skill
claude skill add skills/text-agent-to-strands-voice-agent

# Then ask Claude to use it
# "Migrate my text agent to a Nova Sonic voice agent"
```

### As a Human Developer Guide

Read through the files directly:

1. Start with `SKILL.md` for the full migration walkthrough
2. Pick the closest example in `examples/` for your framework
3. Use `references/voice-prompt-guide.md` to rewrite your system prompt
4. Use `references/server-reference.md` and `references/client-reference.md` for production details

## Validation

The skill follows the [Agent Skills specification](https://agentskills.io/specification):

- `name`: lowercase, hyphens only, under 64 chars
- `description`: under 1024 chars, includes TRIGGER/SKIP keywords
- `SKILL.md`: under 500 lines with YAML frontmatter
- All file references resolve to existing files
- Supplementary content in `references/` and `examples/` per spec conventions
