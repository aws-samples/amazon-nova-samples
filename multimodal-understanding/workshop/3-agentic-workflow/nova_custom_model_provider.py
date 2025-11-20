"""
Nova Custom Model Provider for Strands Framework

This module provides a custom model provider that extends BedrockModel
to automatically strip thinking tags from Nova Foundation Model responses.
"""

import re
from typing import AsyncIterable, Optional, Any
from strands.models import BedrockModel
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec


class NovaCustomModelProvider(BedrockModel):
    """
    Custom model provider for Amazon Nova Foundation Models that automatically
    strips thinking tags from responses while maintaining full BedrockModel compatibility.

    This class extends BedrockModel and adds post-processing to remove
    <thinking>...</thinking> tags and their content from model responses.
    """

    def __init__(self, **kwargs):
        """
        Initialize the NovaCustomModelProvider with the same parameters as BedrockModel.

        Args:
            **kwargs: All keyword arguments are passed directly to the parent BedrockModel.
                     Common parameters include:
                     - model_id (str): Nova model ID like "us.amazon.nova-pro-v1:0"
                     - max_tokens (int): Maximum tokens to generate
                     - temperature (float): Sampling temperature
                     - top_p (float): Top-p sampling parameter
                     - additional_request_fields (dict): Additional Bedrock request parameters
        """
        # Pass all parameters directly to the parent BedrockModel
        super().__init__(**kwargs)
        
        # Initialize streaming buffer for handling partial thinking tags
        self._streaming_buffer = ""
        self._inside_thinking_tag = False

    async def stream(
        self,
        messages: Messages,
        tool_specs: Optional[list[ToolSpec]] = None,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> AsyncIterable[StreamEvent]:
        """
        Generate a streaming response and strip thinking tags from chunks in real-time.

        Args:
            messages: Input messages for the model
            tool_specs: Optional tool specifications
            system_prompt: Optional system prompt
            **kwargs: Additional generation parameters

        Yields:
            StreamEvent: Response chunks with thinking tags removed
        """
        try:
            # Reset streaming state
            self._streaming_buffer = ""
            self._inside_thinking_tag = False
            
            # Get the streaming response from the parent class
            async for event in super().stream(messages, tool_specs, system_prompt, **kwargs):
                # Process the event and yield clean content
                processed_event = self._process_stream_event(event)
                if processed_event is not None:
                    yield processed_event
                    
        except Exception as e:
            # If streaming with tag removal fails, fall back to original streaming
            print(f"Warning: Failed to process streaming with thinking tag removal: {e}")
            async for event in super().stream(messages, tool_specs, system_prompt, **kwargs):
                yield event

    def _process_stream_event(self, event: StreamEvent) -> Optional[StreamEvent]:
        """
        Process a streaming event to remove thinking tags while handling partial tags.

        Args:
            event: A streaming response event

        Returns:
            StreamEvent or None: Processed event with thinking tags removed, or None if filtered
        """
        # Handle contentBlockDelta events which contain the actual text content
        if "contentBlockDelta" in event:
            content_block_delta = event["contentBlockDelta"]
            if "delta" in content_block_delta:
                delta = content_block_delta["delta"]
                if "text" in delta:
                    text_content = delta["text"]
                    
                    # Process the text content through our thinking tag removal
                    clean_content = self._process_streaming_chunk(text_content)
                    
                    if clean_content:
                        # Create a copy of the original event with modified text
                        modified_event = dict(event)
                        modified_event["contentBlockDelta"] = dict(content_block_delta)
                        modified_event["contentBlockDelta"]["delta"] = dict(delta)
                        modified_event["contentBlockDelta"]["delta"]["text"] = clean_content
                        return modified_event
                    else:
                        # Return None to filter out this event
                        return None
        
        # For all other event types, pass them through unchanged
        return event

    def _process_streaming_chunk(self, text_content: str) -> str:
        """
        Process a streaming text chunk to remove thinking tags while handling partial tags.

        Args:
            text_content: Text content from a streaming chunk

        Returns:
            str: Clean content to yield, or empty string if content should be filtered
        """
        if not text_content:
            return ""

        # Add new content to buffer
        self._streaming_buffer += text_content
        
        # Process the buffer to extract clean content
        clean_content = self._extract_clean_content()
        
        return clean_content

    def _extract_clean_content(self):
        """
        Extract clean content from the streaming buffer, handling partial thinking tags.

        Returns:
            str: Clean content that can be safely yielded
        """
        if not self._streaming_buffer:
            return ""

        clean_output = ""
        buffer = self._streaming_buffer
        
        while buffer:
            if not self._inside_thinking_tag:
                # Look for the start of a thinking tag
                thinking_start = buffer.find('<thinking>')
                
                if thinking_start == -1:
                    # No thinking tag found, check for partial tag at the end
                    partial_match = self._find_partial_thinking_start(buffer)
                    if partial_match is not None:
                        # Keep the partial match in buffer, output the rest
                        clean_output += buffer[:partial_match]
                        self._streaming_buffer = buffer[partial_match:]
                        return clean_output
                    else:
                        # No thinking tags, output everything and clear buffer
                        clean_output += buffer
                        self._streaming_buffer = ""
                        return clean_output
                else:
                    # Found start of thinking tag
                    clean_output += buffer[:thinking_start]
                    self._inside_thinking_tag = True
                    buffer = buffer[thinking_start + 10:]  # Skip '<thinking>'
            else:
                # We're inside a thinking tag, look for the end
                thinking_end = buffer.find('</thinking>')
                
                if thinking_end == -1:
                    # No end tag found yet, keep everything in buffer
                    self._streaming_buffer = buffer
                    return clean_output
                else:
                    # Found end tag, skip the thinking content and continue
                    self._inside_thinking_tag = False
                    buffer = buffer[thinking_end + 11:]  # Skip '</thinking>'
        
        # Update buffer with remaining content
        self._streaming_buffer = buffer
        return clean_output

    def _find_partial_thinking_start(self, text):
        """
        Find if there's a partial '<thinking>' tag at the end of the text.

        Args:
            text (str): Text to check for partial thinking tag

        Returns:
            int: Position where partial tag starts, or None if no partial tag
        """
        thinking_tag = '<thinking>'
        
        # Check for partial matches at the end of the text
        for i in range(1, min(len(thinking_tag), len(text)) + 1):
            if text.endswith(thinking_tag[:i]):
                return len(text) - i
        
        return None