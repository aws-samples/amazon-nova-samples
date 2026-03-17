# Amazon Nova 2 Sonic TypeScript Example: Real-time Audio Streaming with AWS Bedrock Integration

This project implements a bidirectional WebSocket-based audio streaming application that integrates with Amazon Nova 2 Sonic model for real-time speech-to-speech conversion. The application enables natural conversational interactions through a web interface while leveraging Amazon's new powerful Nova 2 Sonic model for processing and generating responses.

**Note:** This example uses text input to initiate the conversation, allowing the Nova 2 Sonic model to speak first. Amazon Nova 2 Sonic supports text input, which enables the model to start the conversation naturally by sending a simple text message like "hi" to trigger the initial response.

The system consists of a server that handles the bidirectional streaming and AWS Bedrock integration, paired with a modern web client that manages audio streaming, text input, and user interactions. Key features include real-time audio streaming, text input support, integration with Amazon Nova 2 Sonic model, bidirectional communication handling, and a responsive web interface with chat history management.

## Repository Structure
```
.
├── public/                 # Frontend web application files
│   ├── index.html          # Main application entry point with text input UI
│   └── src/                # Frontend source code
│       ├── lib/            # Core frontend libraries
│       │   ├── play/       # Audio playback components
│       │   └── util/       # Utility functions and managers
│       ├── main.js         # Main application logic with text input support
│       └── style.css       # Application styling including text input
├── src/                    # TypeScript source files
│   ├── client.ts           # AWS Bedrock client with text input support
│   ├── server.ts           # Express server with text input handling
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

The application uses your AWS credentials from:
- Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
- IAM roles (recommended for EC2, ECS, Lambda - provides temporary credentials)
- AWS CLI configuration (~/.aws/credentials)

**Optional:** To use a specific AWS profile:
```bash
export AWS_PROFILE=your-profile-name
```

**First time setup:** If you haven't configured AWS CLI yet:
```bash
aws configure
```

> **Note:** For security best practices, use temporary credentials via IAM roles when running on AWS services.

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

4. Click "Start Streaming" to begin:
   - The app will automatically send "hi" as text input to initiate the conversation
   - Nova 2 Sonic will respond with audio
   - You can continue the conversation using either:
     - Voice input through your microphone
     - Text input using the text field at the bottom of the page

### More Detailed Examples
1. Starting a conversation:
```javascript
// Initialize audio context and request microphone access
await initAudio();
// Click the Start button to begin streaming
startButton.onclick = startStreaming;
```

2. Sending text messages during conversation:
```javascript
// Type a message in the text input field and press Enter, or click Send
function sendTextMessage() {
    const message = textInput.value.trim();
    if (message && isStreaming) {
        socket.emit('textInput', { content: message });
    }
}
```

3. Customizing the system prompt:
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
The application processes both audio and text input through a pipeline that interacts with AWS Bedrock and returns both text and audio responses.

```ascii
User Input (Speech/Text) -> Browser → Server → Client
            ↑                                      ↓
            │                      Amazon Nova 2 Sonic Model
            │                                      ↓
    Audio Output ← Browser ← Server ← Client
```

Key flow components:
1. User provides input through Browser:
   - Speech via microphone for voice input
   - Text via input field for text messages
2. Input is streamed through Server to Client
3. Client sends audio or text to Amazon Nova 2 Sonic Model
4. Nova 2 Sonic processes input and generates AI response
5. Response is sent back through client to server to browser
6. Browser plays audio response and displays text transcription

### Text Input Flow
When using text input to start or continue conversation:
1. User types message in text input field
2. Message is sent via Socket.IO to server
3. Server forwards to Nova 2 Sonic client
4. Client creates proper text input events for Bedrock API
5. Nova 2 Sonic processes text and generates audio response
6. Audio response is streamed back and played to user


## Infrastructure
The application runs on a Node.js server with the following key components:

- Express.js server handling WebSocket connections
- Socket.IO for real-time bidirectional communication
- Nova 2 Sonic client for speech-to-speech and text-to-speech model processing
- Support for both audio streaming and text input

## Key Features

### Text Input Support
- **Initial Conversation Start**: Automatically sends "hi" as text to trigger Nova 2 Sonic to speak first
- **During Conversation**: Users can type messages at any time during the conversation
- **Flexible Input**: Seamlessly switch between voice and text input
- **Real-time Processing**: Text messages are processed instantly and trigger audio responses

### Audio Streaming
- **Real-time Voice Input**: Continuous microphone streaming during active sessions
- **Audio Playback**: High-quality audio responses from Nova 2 Sonic
- **Cross-browser Support**: Works with both Firefox and Chromium-based browsers

### User Interface
- **Chat History**: Visual display of conversation with role labels (USER/ASSISTANT)
- **Text Input Field**: Fixed-position input at bottom of screen for easy access
- **Status Indicators**: Real-time connection and session status
- **Responsive Design**: Adapts to different screen sizes and color schemes (light/dark mode)
