# Amazon Nova Speech-to-Speech FastAPI Server

This project provides a FastAPI-based WebSocket server for Amazon Nova Speech-to-Speech service. It handles bidirectional communication between clients and Amazon Bedrock's Nova Sonic model.

## Features

- WebSocket endpoint for real-time speech-to-speech communication
- Health check endpoints for monitoring
- Integration with MCP (Model Context Protocol) client
- Integration with Strands Agent
- Support for AWS Bedrock bidirectional streaming

## Requirements

- Python 3.8+
- AWS credentials with access to Bedrock
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

Set the following environment variables:

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `AWS_DEFAULT_REGION`: AWS region (defaults to us-east-1)
- `HOST`: Host to bind the server to (defaults to localhost)
- `WS_PORT`: Port for the WebSocket server (defaults to 8081)
- `LOGLEVEL`: Logging level (defaults to INFO)

## Running the Server

Start the FastAPI server:

```
python fastapi_server.py
```

With debug mode:

```
python fastapi_server.py --debug
```

## API Endpoints

- `GET /`: Root endpoint, returns health status
- `GET /health`: Health check endpoint
- `WebSocket /ws`: WebSocket endpoint for speech-to-speech communication

## WebSocket Protocol

The WebSocket endpoint expects JSON messages with the following structure:

```json
{
  "event": {
    "eventType": {
      // Event-specific data
    }
  }
}
```

Event types include:
- `sessionStart`
- `promptStart`
- `contentStart`
- `audioInput`
- `textInput`
- `contentEnd`
- `promptEnd`
- `sessionEnd`
- `APP_CUSTOM_state_update`

## Migration from Original Server

This FastAPI implementation replaces the original WebSocket server (`server.py`). The core functionality remains the same, but with the following improvements:

- Built-in health check endpoints (no separate HTTP server needed)
- Better request handling with FastAPI's dependency injection
- Automatic API documentation via Swagger UI at `/docs`
- More structured application lifecycle management
- Better error handling and logging

To migrate from the original server, simply run `fastapi_server.py` instead of `server.py`.
