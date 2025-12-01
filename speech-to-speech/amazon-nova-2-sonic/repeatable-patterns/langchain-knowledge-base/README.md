# Amazon Nova Sonic with LangChain Knowledge Base Integration

This implementation demonstrates how to integrate Amazon Nova Sonic's speech-to-speech capabilities with a LangChain-powered knowledge base for enhanced conversational experiences.

## Overview

This project combines:

1. **Amazon Nova Sonic** - State-of-the-Art speech-to-speech foundation model that enables natural conversational interactions
2. **LangChain** - A framework for developing applications powered by language models
3. **Knowledge Base** - A vector database created from PDF documents for context-aware responses

## How It Works

1. The system uses `nova_sonic_tool_use.py` to handle bidirectional audio streaming with the Nova Sonic model
2. When a user asks a question about the Aglaia benefit policy, Nova Sonic recognizes it as a tool use case
3. The system calls the `retrieve_benefit_policy` tool, which queries the knowledge base
4. `langchain-kb.py` processes the query against the vector database created from the PDF
5. The relevant information is returned to Nova Sonic, which formulates a natural language response
6. The response is converted to speech and played back to the user

## Implementation Details

### Knowledge Base Setup

The `langchain-kb.py` script:
- Loads the Aglaia_Benefit_Policy.pdf document
- Splits it into manageable chunks
- Creates embeddings using Amazon Bedrock's Titan model
- Stores these embeddings in a Chroma vector database
- Provides retrieval functionality to find relevant information based on queries

### Tool Integration

The `nova_sonic_tool_use.py` script:
- Defines a tool schema for the benefit policy retrieval
- Processes tool use requests from Nova Sonic
- Calls the knowledge base retrieval function
- Returns the results back to Nova Sonic for response generation

## Getting Started

1. Ensure you have all dependencies installed:
   ```bash
   python -m pip install -r requirements.txt
   ```

2. Set up your AWS credentials:
   ```bash
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export AWS_DEFAULT_REGION="us-east-1"
   ```

3. Initialize the knowledge base (this happens automatically on first run):
   ```bash
   python langchain-kb.py
   ```

4. Run the Nova Sonic application with tool use:
   ```bash
   python nova_sonic_tool_use.py
   ```

5. Start a conversation and ask questions about the Aglaia benefit policy

## Example Queries

Try asking Nova Sonic questions like:
- "What medical benefits does Aglaia offer?"
- "Tell me about the vision coverage in the Aglaia policy"
- "What are the retirement benefits at Aglaia?"
- "How does the dental plan work?"

## Technical Architecture

```
User Speech → PyAudio → Nova Sonic → Tool Use Detection → LangChain KB Query → 
                                                                             ↓
                                                                        Vector DB
                                                                             ↓
User ← Audio Output ← Nova Sonic ← Tool Results ← Retrieved Context
```

## Customization

You can extend this implementation by:
- Adding more PDF documents to the knowledge base
- Creating additional tools for different types of queries
- Customizing the system prompt for Nova Sonic
- Adjusting the chunking and retrieval parameters for better results
