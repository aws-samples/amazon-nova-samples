# Amazon Nova Sonic TypeScript Example: Bedrock Knowledge Base Integration

This project demonstrates how to build an intelligent conversational application by integrating Amazon Nova Sonic model with Amazon Bedrock Knowledge Base. The application enables natural speech-to-speech interactions while leveraging a knowledge base to provide accurate, contextual responses about company benefit policies.

## Key Features

- **Knowledge Base Integration**: Retrieves accurate information from company benefit policies stored in Amazon Bedrock Knowledge Base
- **Real-time Speech-to-Speech**: Bidirectional WebSocket-based audio streaming with Amazon Nova Sonic model
- **Natural Conversational Experience**: Seamless interaction through a responsive web interface
- **Contextual Responses**: AI-generated answers informed by knowledge base content
- **Multi-platform Support**: Web interface and command-line options for interactions

## Knowledge Base Integration

This implementation showcases how to enhance AI responses with domain-specific knowledge:

1. **Knowledge Base Creation**: Uses a sample benefit policy document (`kb/Aglaia_Benefit_Policy.pdf`) to create a searchable knowledge base
2. **Tool Schema Integration**: Configures Nova Sonic model with a tool schema for knowledge base queries
3. **Intelligent Retrieval**: Model determines when to use the knowledge base based on user questions
4. **Contextual Response Generation**: Retrieved information is incorporated into natural-sounding responses

### Knowledge Base Workflow

```
User Speech → Amazon Nova Sonic → Tool Use Detection → Bedrock KB Query → 
                                                                             ↓
                                                                        Vector DB
                                                                             ↓
User ← Audio Output ← Amazon Nova Sonic ← Tool Results ← Retrieved Context

```

## Repository Structure
```
.
├── public/                 # Frontend web application files
│   ├── index.html          # Main application entry point
│   └── src/                # Frontend source code
├── src/                    # TypeScript source files
│   ├── client.ts           # AWS Bedrock client implementation
│   ├── bedrock-kb-client.ts # AWS Bedrock Knowledge Base client implementation
│   ├── server.ts           # Express server implementation
│   ├── consts.ts           # Constants including tool schemas and configurations
│   └── types.ts            # TypeScript type definitions
├── kb/                     # Knowledge Base source files
│   └── Aglaia_Benefit_Policy.pdf # Sample benefit policy document for KB
└── tsconfig.json           # TypeScript configuration
```

## Setting Up the Knowledge Base

### Prerequisites
- The latest LTS version of Node.js
- AWS Account with Bedrock access
- AWS CLI configured with appropriate credentials
- Modern web browser with WebAudio API support

### Creating Your Knowledge Base

Before running the application, you must create a Knowledge Base in Amazon Bedrock:

1. **Access the AWS Bedrock Console**:
   - Navigate to the AWS Management Console
   - Search for "Amazon Bedrock" and open the service

2. **Create a New Knowledge Base**:
   - In the left navigation pane, select "Knowledge bases"
   - Click "Create knowledge base"
   - Follow the wizard to create a new knowledge base with vector store
   - Choose a name that reflects your content (e.g., "CompanyBenefitsKB")

3. **Configure Data Source**:
   - Select "Upload files" as your data source by using S3
   - Upload the `kb/Aglaia_Benefit_Policy.pdf` file provided in this repository
   - Configure chunking settings (default settings work well for most cases)

4. **Complete Setup**:
   - Review your settings and create the knowledge base
   - Once created, note your Knowledge Base ID for the next step

5. **Update Application Configuration**:
   - Open `src/client.ts` (around line 280)
   - Replace the placeholder with your actual Knowledge Base ID:

```typescript
// Replace with your actual Knowledge Base ID
const KNOWLEDGE_BASE_ID = 'YOUR_KB_ID_HERE';
```

**Required packages:**

```json
{
  "dependencies": {
    "@aws-sdk/client-bedrock-runtime": "^3.785",
    "@aws-sdk/client-bedrock-agent-runtime": "^3.782",
    "@aws-sdk/credential-providers": "^3.782",
    "@smithy/node-http-handler": "^4.0.4",
    "@smithy/types": "^4.1.0",
    "@types/express": "^5.0.0",
    "@types/node": "^22.13.9",
    "dotenv": "^16.3.1",
    "express": "^4.21.2",
    "pnpm": "^10.6.1",
    "rxjs": "^7.8.2",
    "socket.io": "^4.8.1",
    "ts-node": "^10.9.2",
    "uuid": "^11.1.0"
  }
}
```

## Installation and Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Install dependencies:
```bash
npm install
```

3. Configure AWS credentials:
```bash
# Configure AWS CLI with your credentials
aws configure --profile bedrock-test
```

4. Build the TypeScript code:
```bash
npm run build
```

## Running the Application

1. Start the server:
```bash
npm start
```

2. Open your browser:
```
http://localhost:3000
```

3. Grant microphone permissions when prompted.

4. Start asking questions about company benefits to see the Knowledge Base in action:
  - "What medical benefits does Aglaia offer?"
  - "Tell me about the vision coverage in the Aglaia policy"
  - "What are the retirement benefits at Aglaia?"
  - "How does the dental plan work?"

## Testing Knowledge Base Retrieval

To verify the Knowledge Base integration is working correctly:

1. Ask a question about company benefits
2. The system should:
   - Recognize the question requires knowledge base information
   - Query the knowledge base for relevant content
   - Provide an accurate response based on the benefit policy document

3. Check server logs to see knowledge base retrieval in action:
```bash
# View logs with knowledge base queries
npm start | grep "Knowledge Base"
```

## Troubleshooting Knowledge Base Issues

1. **Knowledge Base Not Responding**:
   - Verify your Knowledge Base ID is correct in `src/client.ts`
   - Check that your AWS credentials have proper permissions
   - Ensure the knowledge base is in "Available" status in the AWS console

2. **Incorrect or Missing Responses**:
   - Verify the document was properly ingested into the knowledge base
   - Check chunking settings in the knowledge base configuration
   - Try rephrasing your question to be more specific

3. **General Connection Issues**:
   - Check server logs for connection status
   - Verify WebSocket connection:
     ```javascript
     socket.on('connect_error', (error) => {
       console.error('Connection failed:', error);
     });
     ```

## Extending the Knowledge Base

To enhance the knowledge base with additional documents:

1. Add new PDF, TXT, or other supported documents to the `kb/` directory
2. Upload these documents to your knowledge base in the AWS Bedrock console
3. No code changes are needed as long as you're using the same knowledge base ID

## Data Flow with Knowledge Base

```ascii
User Question → Browser → Server → Client → Knowledge Base Decision
     ↑                                              ↓
     │                                     Knowledge Base Query
     │                                              ↓
     │                                     Amazon Nova Sonic Model
     │                                              ↓
Audio Response ← Browser ← Server ← Client ← Response Generation
```

## Infrastructure

The application runs on a Node.js server with the following key components:

- Express.js server handling WebSocket connections
- Socket.IO for real-time communication
- Nova Sonic client for speech to speech model processing
- Bedrock Knowledge Base client for information retrieval
