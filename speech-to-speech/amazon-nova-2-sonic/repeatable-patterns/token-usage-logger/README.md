# Amazon Nova 2 Sonic Python Streaming Implementation

This repository contains Python scripts that implement real-time audio streaming applications integrating with Amazon Nova 2 Sonic model. These implementations enable natural conversational interactions through a command-line interface while leveraging Amazon's powerful Nova 2 Sonic model for processing and generating responses.

## Available Implementations

1. **nova_sonic.py**: The full-featured implementation with real bidirectional communication and barge-in support with tool use examples. This allows for more natural conversations where users can interrupt the assistant while it's speaking, similar to human conversations.

## Chat History and Token Usage Logging

This implementation includes a token logging system that captures and preserves all interactions between the user and Nova 2 Sonic, including:

- **Token usage metrics** for monitoring consumption and costs
- Text messages from both user and assistant
- Tool calls made by the assistant
- Tool execution results
- Timestamps for all events
- Barge-in events (when the user interrupts the assistant)

The chat history logger (`chat_history_meter.py`) provides:

1. **Structured Data Capture**: All conversation events are captured in a structured format with appropriate metadata.
2. **JSON Serialization**: Complete conversations can be saved to JSON files for later analysis or playback.
3. **File Management**: Chat histories are automatically saved to the `chat_histories` directory with timestamped filenames.
4. **Chronological Event Tracking**: The system tracks the exact sequence of all events in chronological order, including messages, tool calls, and usage metrics.
5. **Tool Use Tracking**: For implementations using tools, the logger captures both tool calls and their results.
6. **Usage Metrics**: Detailed token consumption tracking for input and output, including speech and text tokens.

Example of a saved chat history file:
```
chat_histories/chat_history_YYYYMMDD_HHMMSS.json
```

This feature is particularly useful for:
- Debugging conversations
- Creating test cases for new features
- Conversation resumption
- Monitoring token usage and costs
- Optimizing prompts for efficiency

### Usage Metrics Tracking

The system captures detailed usage metrics from Nova 2 Sonic in real-time, including:

- Input token counts (speech and text)
- Output token counts (speech and text)
- Total token consumption
- Session and completion IDs for tracking
- Delta metrics showing incremental token usage
- Cumulative metrics showing total usage over time

The chat history meter now provides two different token usage totals:
1. **Delta Sum**: The sum of all incremental token usage reported during the conversation
2. **Final Total**: The total token usage reported in the final usage event

At the end of each conversation, a comprehensive usage summary is displayed:
```
Usage Summary: {
    "delta_sum_calculated": {
        "total_input_tokens": {
            "speechTokens": 209,
            "textTokens": 408,
            "sum": 617
        },
        "total_output_tokens": {
            "speechTokens": 149,
            "textTokens": 69,
            "sum": 218
        },
        "total_tokens": 835
    },
    "final_total": {
        "total_input_tokens": {
            "speechTokens": 209,
            "textTokens": 408,
            "sum": 617
        },
        "total_output_tokens": {
            "speechTokens": 149,
            "textTokens": 69,
            "sum": 218
        },
        "total_tokens": 835
    },
    "final_total_sum": {
        "total_input_tokens": 617,
        "total_output_tokens": 218,
        "total_tokens": 835
    }
}
```

This data is saved in the chat history JSON file for later analysis, with usage events interspersed chronologically with messages and tool interactions to provide a complete timeline of the conversation.

## Features

- Real-time audio streaming from your microphone to AWS Bedrock
- Bidirectional communication with Nova 2 Sonic model
- Audio playback of Nova 2 Sonic responses
- Simple console-based interface showing transcripts
- Support for debug mode with verbose logging
- Barge-in capability
- Tool use integration examples
- Comprehensive chat history logging with chronological event tracking
- Detailed token usage tracking and reporting

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

2. Configure AWS credentials:

The application uses environment variables for AWS authentication. Set these before running the application:

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

## Usage

Run any of the scripts in standard mode:

```bash
# Full implementation with bidirectional communication and barge-in with tool use examples
python nova_sonic.py

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
   - Stream the audio to the Nova 2 Sonic model
   - Play back audio responses through your speakers
   - Display transcripts in the console

2. During the conversation:
   - Your speech will be transcribed and shown as "User: [transcript]"
   - The Nova 2 Sonic's responses will be shown as "Assistant: [response]"
   - Audio responses will be played through your speakers
   - Usage metrics will be collected and logged in real-time
   - All events are recorded in their exact chronological order

3. To end the conversation:
   - Press Enter at any time
   - The script will properly close the connection and exit
   - A comprehensive usage summary will be displayed showing both delta sum and final total token consumption
   - The complete chat history with all events in chronological order will be saved to a file

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

4. **Debug Mode**
   - Run with the `--debug` flag to see detailed logs
   - This can help identify issues with the connection or audio processing

## Data Flow

```
User Speech → PyAudio → Amazon Nova 2 Sonic Model → Tool Execution → Audio Output
     ↑                                                                      ↓
     └──────────────────────────────────────────────────────────────────────┘
                                  Conversation
```
