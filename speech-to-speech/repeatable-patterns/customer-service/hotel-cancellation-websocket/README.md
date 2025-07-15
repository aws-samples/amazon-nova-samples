# Amazon Nova Sonic TypeScript Example: Hotel Reservation Cancellation Customer Service

This example demonstrates a practical customer service use case for Amazon Nova Sonic model, implementing a hotel reservation cancellation system. The application enables natural conversational interactions through a web interface, allowing customers to cancel their hotel reservations through voice commands while interacting with an AI assistant.

The system showcases how businesses can leverage Amazon Nova Sonic model to create seamless, human-like customer service experiences for handling hotel cancellations, including policy explanations, refund calculations, and confirmation processes.

## Use Case Overview

This application simulates a hotel reservation cancellation service with the following workflow:

1. Customer initiates a conversation with the Amazon Nova Sonic
2. Agent verifies customer identity and reservation details (name, check-in date)
3. Agent explains applicable cancellation policies and potential refund amounts
4. Customer confirms cancellation intent
5. Agent processes the cancellation and provides confirmation details
6. Agent delivers a summary of the transaction with next steps

The system demonstrates how to handle real-world customer service scenarios including:
- Reservation lookup by customer name and check-in date
- Dynamic refund calculations based on cancellation policies
- Clear communication of policy terms
- Confirmation workflows to prevent accidental cancellations
- Handling of edge cases like non-existent reservations

## Repository Structure
```
.
├── public/                  # Frontend web application files
│   ├── index.html          # Main application entry point
│   └── src/                # Frontend source code
│       ├── lib/            # Core frontend libraries
│       │   ├── play/       # Audio playback components
│       │   └── util/       # Utility functions and managers
│       ├── main.js         # Main application logic
│       └── style.css       # Application styling
├── src/                    # TypeScript source files
│   ├── client.ts          # AWS Bedrock client implementation
│   ├── server.ts          # Express server implementation
│   ├── hotel-confirmation.ts # Hotel reservation cancellation logic
│   ├── consts.ts          # System prompts and configuration
│   └── types.ts           # TypeScript type definitions
└── tsconfig.json          # TypeScript configuration
```

## Key Features

- **Real-time Voice Interaction**: Bidirectional audio streaming for natural conversations
- **Reservation Verification**: Tool for looking up reservation details by name and date
- **Dynamic Cancellation Policies**: Different refund calculations based on timing and reservation type
- **Confirmation Workflow**: Explicit confirmation required before processing cancellations
- **Refund Calculation**: Automatic calculation of refund amounts based on cancellation policies
- **Confirmation Codes**: Generation of unique cancellation confirmation codes
- **Responsive Web Interface**: User-friendly interface with chat history

## Usage Instructions

### Prerequisites
- The latest LTS version of Node.js
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

### Sample Conversation Flow

Here's an example of how a conversation might flow:

1. **Customer**: "Hi, I need to cancel my hotel reservation."
2. **Agent**: "Hello! I'm here to help you cancel your hotel reservation. Could you please provide your full name and check-in date?"
3. **Customer**: "My name is Angela Park and my check-in date is April 12, 2025."
4. **Agent**: "Thank you, Angela. I've found your reservation at Seaview Hotel for a Deluxe Ocean View room from April 12 to April 15, 2025. According to our policy, you're eligible for a full refund if you cancel by April 5, 2025, or a 50% refund until April 10. Would you like to proceed with cancelling this reservation?"
5. **Customer**: "Yes, please cancel it."
6. **Agent**: "I've processed your cancellation. Your confirmation code is CANX-123456. You'll receive a full refund of $750.00 to your original payment method within 5-7 business days. Is there anything else I can help you with?"

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
     │                   Amazon Nova Sonic Model
     │                               ↓
Audio Output ← Browser ← Server ← Client
```

Key flow components:
1. User speaks into the microphone through Browser
2. Audio is streamed through Server to Client
3. Client sends audio to Amazon Nova Sonic Model with hotel cancellation context
4. Nova Sonic processes audio, uses reservation tools, and generates response
5. Response is sent back through client to server to browser
6. Browser plays audio response to user

## Infrastructure
The application runs on a Node.js server with the following key components:

- Express.js server handling WebSocket connections
- Socket.IO for real-time communication
- Nova S2S client for speech to speech model processing
- Hotel reservation and cancellation business logic
