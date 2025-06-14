# Amazon Nova Sonic Python Streaming Implementation

This repository contains Python scripts that implement real-time audio streaming applications integrating with Amazon Nova Sonic model. These implementations enable natural conversational interactions through a command-line interface while leveraging Amazon's powerful Nova Sonic model for processing and generating responses.

## Available Implementations

This repository includes four different implementations of the Nova Sonic model:

1. **nova_sonic_simple.py**: A basic implementation that demonstrates how events are structured in the bidirectional streaming API. This version does not support barge-in functionality (interrupting the assistant while it's speaking) and does not implement true bidirectional communication.

2. **nova_sonic.py**: The full-featured implementation with real bidirectional communication and barge-in support. This allows for more natural conversations where users can interrupt the assistant while it's speaking, similar to human conversations.

3. **nova_sonic_tool_use.py**: An advanced implementation that extends the bidirectional communication capabilities with tool use examples. This version demonstrates how Nova Sonic can interact with external tools and APIs to provide enhanced functionality.

4. **nova_sonic_file_chat.py**: A specialized implementation that extends the tool use capabilities with a file reading tool. This version allows Nova Sonic to read and analyze local text files through natural conversation, with enhanced command-line file path specification for improved usability and security.

## Features

- Real-time audio streaming from your microphone to AWS Bedrock
- Bidirectional communication with Nova Sonic model
- Audio playback of Nova Sonic responses
- Simple console-based interface showing transcripts
- Support for debug mode with verbose logging
- Barge-in capability (in nova_sonic.py and nova_sonic_tool_use.py)
- Tool use integration examples (in nova_sonic_tool_use.py)
- Local file reading capabilities (in nova_sonic_file_chat.py)

## Prerequisites

- Python 3.12
- AWS Account with Bedrock access
- AWS CLI configured with appropriate credentials
- Working microphone and speakers

## Installation

1. Create and activate a virtual environment:

First, navigate to the root folder of the project and create a virtual environment:

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate
```

2. Install all dependencies:

With the virtual environment activated, install the required packages:

```bash
python -m pip install -r requirements.txt --force-reinstall
```

3. Configure AWS credentials:

The application uses environment variables for AWS authentication. Set these before running the application:

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

## Usage

Run any of the scripts in standard mode:

```bash
# Basic implementation (no barge-in, great start to understand event structure)
python nova_sonic_simple.py

# Full implementation with bidirectional communication and barge-in
python nova_sonic.py

# Advanced implementation with tool use examples
python nova_sonic_tool_use.py

# File chat implementation with local file reading capabilities
python nova_sonic_file_chat.py --file sample_text.txt
```

Or with debug mode for verbose logging:

```bash
python nova_sonic.py --debug
```

### How it works

1. When you run the script, it will:
   - Connect to AWS Bedrock
   - Initialize a streaming session
   - Start capturing audio from your microphone
   - Stream the audio to the Nova Sonic model
   - Play back audio responses through your speakers
   - Display transcripts in the console

2. During the conversation:
   - Your speech will be transcribed and shown as "User: [transcript]"
   - The Nova Sonic's responses will be shown as "Assistant: [response]"
   - Audio responses will be played through your speakers

3. To end the conversation:
   - Press Enter at any time
   - The script will properly close the connection and exit

## Implementation Details

### nova_sonic_simple.py
This implementation provides a basic example of how to interact with the bidirectional streaming API. It:
- Demonstrates the event structure used by Nova Sonic
- Provides a simple one-way communication flow
- Does not support barge-in (interrupting the assistant)
- Does not implement true bidirectional communication
- Useful for understanding the fundamentals of the API

### nova_sonic.py
This is the full-featured implementation that:
- Supports true bidirectional communication
- Implements barge-in functionality allowing users to interrupt the assistant
- Provides a more natural conversational experience
- Handles audio streaming in both directions simultaneously
- Includes improved error handling and session management

### nova_sonic_tool_use.py
This advanced implementation extends the bidirectional capabilities with:
- Tool use examples showing how Nova Sonic can interact with external tools
- Demonstrates how to structure tool use requests and handle responses
- Shows integration patterns for enhancing Nova Sonic with additional capabilities
- Includes examples of practical tool integrations

### nova_sonic_file_chat.py
This specialized implementation focuses on file reading capabilities and includes:
- A custom `readFileTool` that can read local text files
- Command-line file path specification for improved security and usability
- Enhanced tool description that shows the target file being read
- Automatic file path handling without requiring speech input of file paths
- Support for analyzing and discussing file contents through natural conversation
- Built on top of the bidirectional communication and tool use framework

#### File Chat Features:
- **Safe File Access**: File paths are specified via command line, avoiding the need to speak file paths during conversation
- **Automatic File Reading**: When you ask about the file contents, the assistant automatically reads the specified file
- **Content Analysis**: The assistant can analyze, summarize, and discuss the file contents
- **Error Handling**: Graceful handling of missing files or read errors
- **Content Limiting**: File contents are limited to 2000 characters to ensure reasonable response times

#### Example Conversation Flow:
1. Start the application: `python nova_sonic_file_chat.py --file sample_text.txt`
2. Ask: "What is this file about?"
3. The assistant reads the file and provides a summary
4. Continue the conversation to analyze, discuss, or ask questions about the content

## Customization

You can modify the following parameters in the scripts:

- `SAMPLE_RATE`: Audio sample rate (default: 16000 Hz for input, 24000 Hz for output)
- `CHANNELS`: Number of audio channels (default: 1)
- `CHUNK_SIZE`: Audio buffer size (varies by implementation)

You can also customize the system prompt by modifying the `default_system_prompt` variable in the `initialize_stream` method.

## Troubleshooting

1. **Audio Input Issues**
   - Ensure your microphone is properly connected and selected as the default input device
   - Try increasing the chunk size if you experience audio stuttering
   - If you encounter issues with PyAudio installation:

      **On macOS:**
      ```bash
      brew install portaudio
      ```

      **On Ubuntu/Debian:**

      ```bash
      sudo apt-get install portaudio19-dev
      ```

      **On Windows:** 

      ```bash
      # Install PyAudio binary directly using pip
      pip install pipwin
      pipwin install pyaudio
      ```

      Alternatively, Windows users can download pre-compiled PyAudio wheels from:
      https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
      ```bash
      # Example for Python 3.12, 64-bit Windows
      pip install PyAudio‑0.2.11‑cp312‑cp312‑win_amd64.whl
      ```

2. **Audio Output Issues**
   - Verify your speakers are working and not muted
   - Check that the audio output device is properly selected

3. **AWS Connection Issues**
   - Verify your AWS credentials are correctly configured as environment variables
   - Ensure you have access to the AWS Bedrock service
   - Check your internet connection
   - If using temporary credentials, ensure they haven't expired

4. **File Reading Issues (nova_sonic_file_chat.py)**
   - Ensure the file path is correct and the file exists
   - Check file permissions (the application needs read access)
   - Verify the file is a text file (binary files may not display correctly)
   - File content is limited to 2000 characters for performance

5. **Debug Mode**
   - Run with the `--debug` flag to see detailed logs
   - This can help identify issues with the connection or audio processing

## Data Flow

```
User Speech → PyAudio → Amazon Nova Sonic Model → Audio Output
     ↑                                                      ↓
     └──────────────────────────────────────────────────────┘
                          Conversation
```

For tool use implementation, the flow extends to:

```
User Speech → PyAudio → Amazon Nova Sonic Model → Tool Execution → Audio Output
     ↑                                                                      ↓
     └──────────────────────────────────────────────────────────────────────┘
                                  Conversation
```

For file chat implementation, the flow includes file reading:

```
User Speech → PyAudio → Amazon Nova Sonic Model → File Reading Tool → Audio Output
     ↑                                                                        ↓
     └────────────────────────────────────────────────────────────────────────┘
                                    File-Enhanced Conversation
```

## Known Limitation
> **Warning:** Use a headset for testing, as a known issue with PyAudio affects its handling of echo. You may experience unexpected interruptions if running the samples with open speakers.
