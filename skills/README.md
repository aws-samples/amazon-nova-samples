# Amazon Nova Skills

Reusable [Agent Skills](https://agentskills.io/specification) for building with Amazon Nova models. Each skill provides step-by-step guidance that AI coding assistants (Kiro, Claude Code, etc.) can follow to help you build faster.

## Available Skills

| Skill | Description |
|-------|-------------|
| [text-agent-to-strands-voice-agent](./text-agent-to-strands-voice-agent/) | Migrate a text-based agent to a real-time voice agent using Strands BidiAgent with Amazon Nova Sonic |
| [nova-prompter](./nova-prompter/) | Write and optimize prompts for Amazon Nova 1 and Nova 2 Lite — Claude Code plugins (`/nova1-prompt`, `/nova2-prompt`) and matching Kiro powers, with multimodal coverage for Nova 2 |
| [titan-nova-mme-migration](./titan-nova-mme-migration/) | Migrate Amazon Bedrock embedding code from Titan Text V2 / Titan Multimodal G1 to Amazon Nova Multimodal Embeddings — handles request schema, dimension mapping, `embeddingPurpose`, and client-side text+image fusion |
| [gemini-to-nova-migration](./gemini-to-nova-migration/) | Migrate Google Gemini 2.0/2.5/3.x Python code and prompts to Amazon Nova 2 Lite — converts SDK calls (`google-genai` / `google-generativeai` → `boto3` Bedrock `converse`), rewrites prompts to `##Section##` format, handles multimodal, tool calling, structured output, streaming, and reasoning mode |
| [openai-to-nova-migration](./openai-to-nova-migration/) | Migrate OpenAI GPT-4o/4.1/5.x Python code and prompts to Amazon Nova 2 Lite — from either the OpenAI API (Chat Completions, Responses, Assistants) or OpenAI hosted on Amazon Bedrock (GPT-5.5/5.4 via Responses, gpt-oss via Converse); extracts system prompts, nests inference params, rewrites prompts to `##Section##` format, and handles multimodal, tool calling, structured output, streaming, and extended thinking |