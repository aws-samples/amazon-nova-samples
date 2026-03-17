# Amazon Nova 2 Sonic WebSocket Example (.NET Version)

This project implements a bidirectional WebSocket-based audio streaming application that integrates with Amazon Nova 2 Sonic model for real-time speech-to-speech conversion. The application enables natural conversational interactions through a web interface while leveraging Amazon's powerful Speech to Speech model for processing and generating responses.

The system consists of a .NET-based WebSocket server that handles the core communication and AWS Bedrock integration, paired with a modern web client that manages audio streaming and user interactions. Key features include real-time audio streaming, integration with Amazon Nova 2 Sonic model, bidirectional communication handling, cross-browser support (including Firefox), and a responsive web interface with chat history management. The application implements the Observer pattern using ReactiveX for handling events and provides comprehensive error handling and logging capabilities.

## Repository Structure
```
websocket-dotnet/
├── WebSocket/                    # WebSocket server implementation
│   ├── WebSocketServer.cs        # Main server component
│   └── InteractWebSocket.cs      # WebSocket endpoint implementation
├── Utility/                      # Core business logic
│   ├── NovaSonicBedrockInteractClient.cs  # AWS Bedrock client with Nova 2 Sonic integration
│   ├── NovaSonicResponseHandler.cs        # Response handling
│   ├── InputEventsInteractObserver.cs     # Input event observer
│   ├── OutputEventsInteractObserver.cs    # Output event observer
│   ├── IInteractObserver.cs               # Observer interface
│   └── AtomicBoolean.cs                   # Thread-safe boolean
├── ui-stream/                    # Web UI client
│   ├── src/                      # UI source code
│   │   ├── main.js               # Main UI logic with Firefox support
│   │   └── websocketEvents.js    # WebSocket event handling
│   └── index.html                # UI entry point
├── Program.cs                    # Main entry point
└── NovaSonicWebSocket.csproj     # Project file
```

## Usage Instructions

### Prerequisites
- .NET 9.0 SDK or higher
- AWS account with Bedrock access
- AWS credentials configured locally

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd amazon-nova-samples/speech-to-speech/sample-codes/websocket-dotnet
```

2. Configure AWS credentials:

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
# Configure AWS CLI with your credentials
aws configure
```

> **Note:** For security best practices, use temporary credentials via IAM roles when running on AWS services.

3. Build and run the .NET application:
```bash
dotnet build
dotnet run
```

4. Start the UI client:
```bash
cd ui-stream
npm install
npm run dev
```

### Quick Start

1. Start the .NET WebSocket server:
```bash
dotnet run
```

2. Open your browser (Chrome, Firefox, or other modern browsers) and navigate to `http://localhost:5173`

3. Configure the application (optional):
   - Click the Configuration panel to expand settings
   - Select your preferred voice from the dropdown (default: Tiffany)
   - The system prompt will automatically update based on voice gender
   - Available voices:
     - **English**: matthew, tiffany, amy, olivia
     - **Spanish**: lupe, carlos
     - **French**: ambre, florian
     - **German**: tina, lennart
     - **Italian**: beatrice, lorenzo
     - **Portuguese**: carolina, leo
     - **Hindi**: arjun, kiara

4. Start the conversation:
   - Click "Start Streaming" to begin
   - Speak into your microphone for voice input
   - Or type messages in the text input field at the bottom
   - The assistant will respond with audio and text transcription

**Note**: This implementation includes cross-browser support with special handling for Firefox's audio context requirements.

### Logging Configuration

The application uses Microsoft.Extensions.Logging with configurable log levels. By default, the log level is set to `Information` in `Program.cs`.

To enable more detailed debug logging, modify the log level in `Program.cs`:

```csharp
// Configure logging
using var loggerFactory = LoggerFactory.Create(builder =>
{
    builder
        .SetMinimumLevel(LogLevel.Debug)  // Change from Information to Debug
        .AddConsole();
});
```

Log levels used in this application (from most to least verbose):
- `LogLevel.Debug` - Detailed logs for debugging, includes tool processing details, payloads, and chat history
- `LogLevel.Information` - General informational messages (default) - session events, completion events, tool use notifications
- `LogLevel.Warning` - Warning messages for potentially harmful situations - null data, unhandled tools
- `LogLevel.Error` - Error messages for failures - WebSocket errors, AWS errors, tool processing failures

**Recommended settings:**
- **Development/Debugging**: Use `LogLevel.Debug` to see detailed tool processing, payload information, and internal state changes
- **Production**: Use `LogLevel.Information` (default) for general operational logs without excessive detail

### Troubleshooting

#### WebSocket Connection Issues
- Error: "Connection refused"
  1. Verify the server is running
  2. Ensure port 8081 is available: `netstat -an | grep 8081`

#### AWS Credentials Issues
- Error: "Unable to load AWS credentials"
  1. Verify AWS credentials file: `cat ~/.aws/credentials`
  2. Check environment variables: `echo $AWS_ACCESS_KEY_ID`
  3. Ensure AWS CLI is configured: `aws configure list`

#### .NET Framework Issues
- Error: "You must install or update .NET to run this application"
  1. Check installed .NET versions: `dotnet --list-runtimes`
  2. Install .NET 9.0: `brew install --cask dotnet-sdk`
  3. Or update project to match your installed version in `NovaSonicWebSocket.csproj`

## Data Flow

The application implements a bidirectional streaming architecture with support for both audio and text input:

```ascii
User Input (Voice/Text) -> Browser → WebSocket → .NET Backend
         ↑                                            ↓
         │                              Amazon Nova 2 Sonic Model
         │                                            ↓
Audio/Text Output ← Browser ← WebSocket ← .NET Backend
```

Key flow components:
1. User provides input through Browser:
   - **Voice input**: Speaks into the microphone (with Firefox-specific audio handling)
   - **Text input**: Types message in the text input field
2. Audio is resampled to 16kHz if necessary (Firefox compatibility)
3. Input is streamed through WebSocket to .NET backend
4. Backend sends audio or text to Amazon Nova 2 Sonic Model
5. Nova 2 Sonic processes input and generates AI response
6. Response is sent back through backend to browser
7. Browser plays audio response and displays text transcription

### Text Input Flow
When using text input during conversation:
1. User types message in the text input field
2. Message is sent via WebSocket to .NET backend as JSON event
3. Backend forwards the text input event to Nova 2 Sonic client
4. Client creates proper text input events (contentStart, textInput, contentEnd) for Bedrock API
5. Nova 2 Sonic processes text and generates audio response
6. Audio response is streamed back and played to user

### Browser Compatibility

The UI client includes special handling for Firefox:
- **Audio Context**: Firefox requires using the native sample rate of the user's media device, while Chromium browsers can specify a custom sample rate
- **Resampling**: The application automatically detects Firefox and applies proper audio resampling to ensure 16kHz audio is sent to the Nova 2 Sonic model
- **Sample Rate Detection**: The UI logs the detected sample rate and sampling ratio for debugging purposes

## Infrastructure

```ascii
[Browser Client (Chrome/Firefox)]
      ↕
[WebSocket Server (.NET)]
      ↕
[Amazon Nova 2 Sonic Model]
```

### WebSocket Components
- WebSocketServer: Main server component (port 8081)
- InteractWebSocket: WebSocket endpoint implementation
- NovaSonicBedrockInteractClient: AWS Bedrock client with Nova 2 Sonic (model ID: amazon.nova-2-sonic-v1:0)

### Key Features
- **Real-time Audio Streaming**: Bidirectional audio streaming with low latency
- **Text Input Support**: Send text messages at any time during conversation
- **Cross-Browser Support**: Works seamlessly with Chrome, Firefox, and other modern browsers
- **Firefox-Specific Handling**: Automatic audio resampling for Firefox compatibility
- **Multiple Voice Options**: Support for 15 voices across 7 languages (English, Spanish, French, German, Italian, Portuguese, Hindi)
- **Gender-Aware System Prompts**: Automatically adjusts assistant persona based on selected voice
- **Event Logging**: Comprehensive event viewer for debugging and monitoring
- **Chat History**: Visual display of conversation with transcriptions
- **Tool Support**: Integration with custom tools and function calling
