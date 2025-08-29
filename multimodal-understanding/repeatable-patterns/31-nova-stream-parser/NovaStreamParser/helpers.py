import json

"""
Helper functions for processing streaming responses from AWS Bedrock models.

This module provides utility functions to extract, validate, and process different parts
of streaming response events from AWS Bedrock models, particularly focusing on content
blocks and tool use functionality.

Functions:
- get_block_for_invoke_model_with_streaming: Extracts and decodes JSON payload from streaming events
- get_block_for_converse_streaming: Assume that block is JSON, not binary, and returns the event directly for converse streaming
- is_content_block_start_valid: Validates if a block contains a valid content block start with tool use
- is_content_block_delta_valid: Checks if a block contains a valid content block delta
- is_content_block_delta_text_valid: Verifies if a content block delta contains text
- is_content_block_delta_tool_use_valid: Validates if a content block delta contains tool use input
"""

# used with Bedrock invoke_model_with_response_stream
def get_block_for_invoke_model_with_response_stream(event):
        block = json.loads(event.get('chunk').get('bytes').decode())
        return block

# used with Bedrock converse_stream
def get_block_for_converse_streaming(event):
        return event

def is_content_block_start_valid(block) -> bool:
    return (block is not None
            and block.get("contentBlockStart") is not None
            and block["contentBlockStart"].get("start") is not None
            and block["contentBlockStart"]["start"].get("toolUse") is not None
            and block["contentBlockStart"]["start"]["toolUse"].get("toolUseId") is not None
            and block["contentBlockStart"]["start"]["toolUse"].get("name") is not None)

def is_content_block_delta_valid(block) -> bool:
    return (block is not None
            and block.get("contentBlockDelta") is not None
            and block["contentBlockDelta"].get("delta") is not None)

def is_content_block_delta_text_valid(block) -> bool:
    return block["contentBlockDelta"]["delta"].get("text") is not None

def is_content_block_delta_tool_use_valid(block) -> bool:
    return (block["contentBlockDelta"]["delta"].get("toolUse") is not None
            and block["contentBlockDelta"]["delta"]["toolUse"].get("input") is not None)
