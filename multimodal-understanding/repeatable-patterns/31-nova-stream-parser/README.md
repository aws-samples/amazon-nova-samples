# NovaStreamParser

A Python package for parsing and processing streaming responses from AWS Bedrock Nova models. NovaStreamParser provides decorators that enable extraction of content between specified XML tags from both `invoke_model_with_response_stream` and `converse_stream` API responses.

## Features

- **Decorator-based API**: Simple decorators to wrap your stream processing functions
- **XML Tag Extraction**: Extract content between specified XML tags (e.g., `<thinking>` tags)
- **Dual Stream Support**: Works with both `invoke_model_with_response_stream` and `converse_stream` APIs
- **Event-based Processing**: Handles different event types (messageStart, contentBlockDelta, messageStop, metadata)
- **Real-time Processing**: Processes streaming responses as they arrive

## Installation

### Prerequisites

- Python 3.12 or higher
- AWS credentials configured (via AWS CLI, environment variables, or IAM roles)

### Dependencies

Install the required dependencies:

```bash
pip install boto3>=1.39.9
```

### Package Installation

Since this is a local package, you can install it in development mode:

```bash
# From the project root directory
pip install -e .
```

Or simply ensure the `NovaStreamParser` directory is in your Python path.

## Quick Start

### Basic Usage

```python
import boto3
import json
from NovaStreamParser.nova_parsed_event_stream import (
    parse_invoke_model_with_response_stream,
    parse_converse_stream
)

# Create Bedrock Runtime client
client = boto3.client("bedrock-runtime", region_name="us-east-1")
```

### Example 1: Using with invoke_model_with_response_stream

```python
@parse_invoke_model_with_response_stream(target_tag_name="thinking")
def process_invoke_model_with_response_stream(response_stream):
    return response_stream

# Make the API call
response = client.invoke_model_with_response_stream(
    modelId="us.amazon.nova-lite-v1:0",
    body=json.dumps(your_request_body)
)

response_stream = response.get('body')

# Process the stream - content within <thinking> tags will be extracted
for event in process_invoke_model_with_response_stream(response_stream):
    print(event)
```

### Example 2: Using with converse_stream

```python
@parse_converse_stream("thinking")
def process_converse_stream(response_stream):
    return response_stream

# Make the API call
response = client.converse_stream(
    modelId="us.amazon.nova-lite-v1:0",
    messages=messages,
    system=system_prompt,
    inferenceConfig=inference_config,
    toolConfig=tool_config
)

response_stream = response.get('stream')

# Process the stream - content within <thinking> tags will be extracted
for event in process_converse_stream(response_stream):
    print(event)
```

## API Reference

### Decorators

#### `@parse_converse_stream(target_tag_name)`

Decorator for processing `converse_stream` API responses.

**Parameters:**
- `target_tag_name` (str): The XML tag name to extract content from (e.g., "thinking")

**Usage:**
```python
@parse_converse_stream("thinking")
def your_stream_function(response_stream):
    return response_stream
```

#### `@parse_invoke_model_with_response_stream(target_tag_name)`

Decorator for processing `invoke_model_with_response_stream` API responses.

**Parameters:**
- `target_tag_name` (str): The XML tag name to extract content from (e.g., "thinking")

**Usage:**
```python
@parse_invoke_model_with_response_stream(target_tag_name="thinking")
def your_stream_function(response_stream):
    return response_stream
```

## Complete Example

Here's a complete working example that demonstrates both decorators:

```python
import boto3
import json
from NovaStreamParser.nova_parsed_event_stream import (
    parse_invoke_model_with_response_stream,
    parse_converse_stream
)

# Decorated functions
@parse_converse_stream("thinking")
def process_converse_stream(response_stream):
    return response_stream

@parse_invoke_model_with_response_stream(target_tag_name="thinking")
def process_invoke_model_with_response_stream(response_stream):
    return response_stream

# Configuration
system_text = """
You are a helpful assistant that answers questions about the weather.
When reasoning on your replies, place the reasoning in <thinking></thinking> tags.
"""

system_prompt = [{"text": system_text}]
inference_config = {"maxTokens": 1024, "topP": 0.9, "temperature": 0.7}

messages = [
    {
        "role": "user",
        "content": [{"text": "What's the weather like in Seattle?"}]
    }
]

body = {
    "system": system_prompt,
    "inferenceConfig": inference_config,
    "messages": messages
}

MODEL_ID = "us.amazon.nova-lite-v1:0"
client = boto3.client("bedrock-runtime", region_name="us-east-1")

# Example 1: invoke_model_with_response_stream
print("--- Invoke Model Stream ---")
response = client.invoke_model_with_response_stream(
    modelId=MODEL_ID,
    body=json.dumps(body)
)

response_stream = response.get('body')
for event in process_invoke_model_with_response_stream(response_stream):
    print(event)

# Example 2: converse_stream
print("--- Converse Stream ---")
response = client.converse_stream(
    modelId=MODEL_ID,
    messages=body["messages"],
    system=body["system"],
    inferenceConfig=body["inferenceConfig"]
)

response_stream = response.get('stream')
for event in process_converse_stream(response_stream):
    print(event)
```

## How It Works

1. **Decoration**: The decorators wrap your stream processing functions
2. **Stream Interception**: The original response stream is intercepted and processed
3. **Event Processing**: Different event types are handled appropriately:
   - `messageStart`: Initialization
   - `contentBlockDelta`: Content processing and tag extraction
   - `messageStop`: Finalization
   - `metadata`: Stream completion
4. **Tag Extraction**: Content within the specified XML tags is extracted and made available
5. **Stream Generation**: A new processed stream is generated with the extracted content

## Requirements

- AWS Bedrock access with Nova model permissions
- Properly configured AWS credentials
- Python 3.12+
- boto3 >= 1.39.9

## Error Handling

The package includes basic error handling:
- Validates that `target_tag_name` is provided
- Handles different event types gracefully
- Manages stream lifecycle properly

## Contributing

This package is part of a larger codebase. For issues or contributions, please refer to the project maintainers.

## License

Please refer to the project's license file for licensing information.
