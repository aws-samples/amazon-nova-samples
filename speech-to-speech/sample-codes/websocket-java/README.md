# Amazon Nova Sonic WebSocket Example: Real-time Audio Streaming with AWS Bedrock Integration

This project implements a bidirectional WebSocket-based audio streaming application that integrates with Amazon Nova Sonic model for real-time speech-to-speech conversion. The application enables natural conversational interactions through a web interface while leveraging Amazon's new powerful Speech to Speech model for processing and generating responses.

The system consists of a Java-based WebSocket server that handles the core communication and AWS Bedrock integration, paired with a modern web client that manages audio streaming and user interactions. Key features include real-time audio streaming, integration with Amazon Nova Sonic model, bidirectional communication handling, and a responsive web interface with chat history management. The application implements the Observer pattern for handling events and provides comprehensive error handling and logging capabilities.

## Repository Structure
```
websocket-java/
├── app/                          # Core Java application
│   ├── src/
│   │   ├── main/java/org/example/
│   │   │   ├── BedrockInitiateClient.java    # Main entry point
│   │   │   ├── utility/                      # Core business logic
│   │   │   └── websocket/                    # WebSocket implementation
│   │   └── resources/
│   │       └── log4j2.xml                    # Logging configuration
├── ui-stream/                    # Web client implementation
│   ├── src/
│   │   ├── lib/
│   │   │   ├── play/                         # Audio playback handling
│   │   │   └── util/                         # Client utilities
│   │   └── main.js                           # Client entry point
└── docs/                         # Infrastructure documentation
```

## Usage Instructions

### Prerequisites
- Java 17 or higher
- The latest LTS version of Node.js
- AWS account with Bedrock access
- AWS credentials configured locally

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd NovaSonicWebSocketExample
```

2. Configure AWS credentials:
```bash
# Configure AWS CLI with your credentials
aws configure --profile bedrock-test
```

3. Build and run the Java application:
```bash
gradle build
gradle run
```

4. Install UI dependencies:
```bash
cd ui-stream
npm install
```

### Quick Start

1. Start the UI development server:
```bash
cd ui-stream
npm run dev
```

2. Open your browser and navigate to `http://localhost:5173`

### Troubleshooting

#### WebSocket Connection Issues
- Error: "Connection refused"
  1. Verify the server is running: `ps aux | grep BedrockInitiateClient`
  2. Ensure port 8081 is available: `netstat -an | grep 8081`

#### AWS Credentials Issues
- Error: "Unable to load AWS credentials"
  1. Verify AWS credentials file: `cat ~/.aws/credentials`
  2. Check environment variables: `echo $AWS_ACCESS_KEY_ID`
  3. Ensure AWS CLI is configured: `aws configure list`

#### Audio Streaming Issues
- Enable debug logging by modifying `log4j2.xml`:
```xml
<Root level="debug">
    <AppenderRef ref="Console"/>
</Root>
```

## Data Flow

The application implements a bidirectional streaming architecture with the following flow:

```ascii
User Speech -> Browser → WebSocket → Java Backend 
     ↑                                     ↓
     │                         Amazon Nova Sonic Model
     │                                     ↓
Audio Output ← Browser ← WebSocket ← Java Backend
```


Key flow components:
1. User speaks into the microphone through Browser
2. Audio is streamed through WebSocket to Java backend
3. Backend sends audio to Amazon Nova Sonic Model
4. Nova Sonic processes audio and generates AI response
5. Response is sent back through backend to browser
6. Browser plays audio response to user

## Infrastructure

```ascii
[Browser Client]
      ↕
[WebSocket Server]
      ↕
[Amazon Nova Sonic Model]
```

### WebSocket Components
- WebSocketServer: Main server component (port 8081)
- InteractWebSocket: WebSocket endpoint implementation
- NovaSonicBedrockInteractClient: AWS Bedrock client integration
