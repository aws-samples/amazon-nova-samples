# Amazon Nova Skills

Reusable [Agent Skills](https://agentskills.io/specification) for building with Amazon Nova models. Each skill provides step-by-step guidance that AI coding assistants (Kiro, Claude Code, etc.) can follow to help you build faster.

## Available Skills

| Skill | Description |
|-------|-------------|
| [text-agent-to-strands-voice-agent](./text-agent-to-strands-voice-agent/) | Migrate a text-based agent to a real-time voice agent using Strands BidiAgent with Amazon Nova Sonic |
| [nova-prompter](./nova-prompter/) | Write and optimize prompts for Amazon Nova 1 and Nova 2 Lite — Claude Code plugins (`/nova1-prompt`, `/nova2-prompt`) and matching Kiro powers, with multimodal coverage for Nova 2 |
| [titan-nova-mme-migration](./titan-nova-mme-migration/) | Migrate Amazon Bedrock embedding code from Titan Text V2 / Titan Multimodal G1 to Amazon Nova Multimodal Embeddings — handles request schema, dimension mapping, `embeddingPurpose`, and client-side text+image fusion |
| [nova-api-migration](./nova-api-migration/) | Unified API code migration from Google Gemini, OpenAI, or Anthropic Claude to Amazon Nova 2 Lite — handles SDK swap, auth, request/response reshaping, tool calling, structured output, multimodal, streaming, and reasoning config across all three providers |