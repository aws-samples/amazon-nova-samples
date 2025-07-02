# Amazon Nova Sonic TypeScript Example: Conversation Resumption

This example demonstrates how to implement conversation resumption capabilities with Amazon Nova Sonic model. Using a hotel reservation cancellation scenario as the context, the application shows how to maintain conversation state across sessions, allowing users to seamlessly continue interactions that were previously interrupted.

## Conversation Resumption Overview

The primary focus of this example is to showcase how Nova Sonic can maintain context across conversation sessions by:

1. Reloading the conversation history when a user continues the conversation
3. Enabling the model to pick up exactly where the conversation left off
4. Providing a natural, seamless experience for the user

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

## Key Conversation Resumption Features

- **Context Preservation**: Maintains full conversation history between sessions
- **Seamless Continuation**: Allows users to resume exactly where they left off
- **State Management**: Preserves user identity and conversation progress
- **Natural Transitions**: Creates fluid conversation flow despite interruptions

## Technical Implementation

The conversation resumption feature is implemented in the server code using the following approach:

```javascript
// Here we are sending the conversation history to resume the conversation
// This set of events need to be sent after system prompt before audio stream starts
socket.on('conversationResumption', async () => {
    try {
        console.log('Resume conversation for Don Smith, check in date is 2025-05-15');
        // USER: hi there i would like to cancel my hotel reservation
        // ASSISTANT: Hello! I'd be happy to assist you with cancelling your hotel reservation. To get started, could you please provide me with your full name and the check-in date for your reservation?
        // USER: yeah so my name is don smith
        // ASSISTANT: Thank you, Don. Now, could you please provide me with the check-in date for your reservation?
        // USER: yes so um let me check just a second
        // ASSISTANT: Take your time, Don. I'll be here when you're ready.

        // USER needs to start the conversation with checkin date; checkin date for Don is May 15, 2025

        await session.setupHistoryForConversationResumtion(undefined, "hi there i would like to cancel my hotel reservation", "USER");
        await session.setupHistoryForConversationResumtion(undefined, "Hello! I'd be happy to assist you with cancelling your hotel reservation. To get started, could you please provide me with your full name and the check-in date for your reservation?", "ASSISTANT");
        await session.setupHistoryForConversationResumtion(undefined, "yeah so my name is don smith", "USER");
        await session.setupHistoryForConversationResumtion(undefined, "Thank you, Don. Now, could you please provide me with the check-in date for your reservation?", "ASSISTANT");
        await session.setupHistoryForConversationResumtion(undefined, "yes so um let me check just a second", "USER");
        await session.setupHistoryForConversationResumtion(undefined, "Take your time, Don. I'll be here when you're ready.", "ASSISTANT");
    } catch (error) {
        console.error('Error processing system prompt:', error);
        socket.emit('error', {
            message: 'Error processing system prompt',
            details: error instanceof Error ? error.message : String(error)
        });
    }
});
```

## How Conversation Resumption Works

### 1. Conversation History Storage

The example demonstrates storing a conversation history for a user named "Don Smith" who previously:
- Initiated a request to cancel a hotel reservation
- Provided his name
- Was asked for his check-in date but needed time to look it up

### 2. Resumption Sequence

The conversation resumption follows this sequence:
1. Set up the system prompt with the hotel cancellation context
2. Load the previous conversation history using `setupHistoryForConversationResumtion`
3. Start the audio stream
4. User continues the conversation by providing the check-in date

### 3. Key Methods for Implementation

The implementation uses two important methods:

1. **setupHistoryForConversationResumtion**: Adds a message to the conversation history with the specified role (USER or ASSISTANT). Parameters:
   - Message content as a string
   - Role of the message sender ("USER" or "ASSISTANT")

2. **setupHistoryEventForConversationResumption**: Creates relevant contentStart, textInput and contentEnd events for each role and pass them to the model in order.

## Testing the Conversation Resumption

To test the conversation resumption feature:

1. The system is pre-configured with a partial conversation for "Don Smith"
2. Start the application and connect to the web interface
3. Begin by saying: "My check-in date is May 15, 2025"
4. The system will recognize this as a continuation of Don's previous conversation with context of:
   - Don has already identified himself
   - Don wants to cancel a reservation
   - The system was waiting for Don to provide his check-in date

## Implementation Requirements

For proper conversation resumption:

1. The conversation history must be sent after the system prompt is set
2. It needs to be sent before the audio stream starts
3. Messages must be added in the correct order with content blocks
4. Both user and assistant messages must be included to maintain context

## Usage Instructions

### Prerequisites
- Node.js (v14 or higher)
- AWS Account with Bedrock access
- AWS CLI configured with appropriate credentials
- Modern web browser with WebAudio API support

### Quick Start
1. Install dependencies: `npm install`
2. Configure AWS credentials: `aws configure --profile bedrock-test`
3. Build the TypeScript code: `npm run build`
4. Start the server: `npm start`
5. Open your browser: `http://localhost:3000`
6. Grant microphone permissions when prompted
7. Test resumption by saying: "My check-in date is May 15, 2025"


## When to Use Conversation Resumption

- Conversation context needs to be carried over to a new connection
- This approach is particularly helpful for error recovery in these scenarios:
  - After receiving a ModelTimeoutException with the message "Model has timed out in processing the request"
  - When needing to restore context after an unexpected disconnection




