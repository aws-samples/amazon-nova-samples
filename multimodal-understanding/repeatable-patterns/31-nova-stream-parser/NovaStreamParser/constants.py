"""
Constants for the NovaStreamParser module.

This module defines string constants used throughout the NovaStreamParser package
to identify different types of streaming modes when interacting with AWS Bedrock
Nova models.

Constants:
- INVOKE_STREAM: Identifier for the invoke_model_with_response_stream API mode
- CONVERSE_STREAM: Identifier for the converse streaming API mode
"""

INVOKE_STREAM = "invoke"
CONVERSE_STREAM = "converse"