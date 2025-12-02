# Amazon Nova 2 Sonic TypeScript Example: Real-time Audio Streaming with AWS Bedrock Integration

This project implements a bidirectional WebSocket-based audio streaming application that integrates with Amazon Nova 2 Sonic model for real-time speech-to-speech conversion. The application enables natural conversational interactions through a web interface while leveraging Amazon's new powerful Nova 2 Sonic model for processing and generating responses.

The system consists of a server that handles the bidirectional streaming and AWS Bedrock integration, paired with a modern web client that manages audio streaming and user interactions. Key features include real-time audio streaming, integration with Amazon Nova 2 Sonic model, bidirectional communication handling, and a responsive web interface with chat history management. It supports also command-line interface to run an interaction with a recorded audio.

## Repository Structure
```
.
├── public/                 # Frontend web application files
│   ├── index.html          # Main application entry point
│   └── src/                # Frontend source code
│       ├── lib/            # Core frontend libraries
│       │   ├── play/       # Audio playback components
│       │   └── util/       # Utility functions and managers
│       ├── main.js         # Main application logic
│       └── style.css       # Application styling
├── src/                    # TypeScript source files
│   ├── client.ts           # AWS Bedrock client implementation
│   ├── server.ts           # Express server implementation
│   └── types.ts            # TypeScript type definitions
└── tsconfig.json           # TypeScript configuration
```

## Usage Instructions
### Prerequisites
- Node.js (v14 or higher)
- AWS Account with Bedrock access
- AWS CLI configured with appropriate credentials
- Modern web browser with WebAudio API support

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

### Installation
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

### Quick Start
1. Start the server:
```bash
npm start
```

2. Open your browser:
```
http://localhost:3000
```

3. Grant microphone permissions when prompted.

### More Detailed Examples
1. Starting a conversation:
```javascript
// Initialize audio context and request microphone access
await initAudio();
// Click the Start button to begin streaming
startButton.onclick = startStreaming;
```

2. Customizing the system prompt:
```javascript
const SYSTEM_PROMPT = "You are a friend. The user and you will engage in a spoken...";
socket.emit('systemPrompt', SYSTEM_PROMPT);
```

### Troubleshooting
1. Microphone Access Issues
- Problem: Browser shows "Permission denied for microphone"
- Solution: 
  ```javascript
  // Check if microphone permissions are granted
  const permissions = await navigator.permissions.query({ name: 'microphone' });
  if (permissions.state === 'denied') {
    console.error('Microphone access is required');
  }
  ```

2. Audio Playback Issues
- Problem: No audio output
- Solution:
  ```javascript
  // Verify AudioContext is initialized
  if (audioContext.state === 'suspended') {
    await audioContext.resume();
  }
  ```

3. Connection Issues
- Check server logs for connection status
- Verify WebSocket connection:
  ```javascript
  socket.on('connect_error', (error) => {
    console.error('Connection failed:', error);
  });
  ```

## Data Flow
The application processes audio input through a pipeline that converts speech to text, processes it with AWS Bedrock, and returns both text and audio responses.

```ascii
User Speech -> Browser → Server → Client
     ↑                               ↓
     │                   Amazon Nova 2 Sonic Model
     │                               ↓
Audio Output ← Browser ← Server ← Client
```

Key flow components:
1. User speaks into the microphone through Browser
2. Audio is streamed through Server to Client
3. Client sends audio to Amazon Nova 2 Sonic Model
4. Nova 2 Sonic processes audio and generates AI response
5. Response is sent back through client to server to browser
6. Browser plays audio response to user


## Infrastructure
The application runs on a Node.js server with the following key components:

- Express.js server handling WebSocket connections
- Socket.IO for real-time communication
- Nova 2 Sonic client for speech to speech model processing
