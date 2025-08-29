from .constants import INVOKE_STREAM, CONVERSE_STREAM
from .nova_event_stream import NovaEventStream
from .helpers import (
    get_block_for_invoke_model_with_response_stream, 
    get_block_for_converse_streaming
)
from .nova_response_stream_handler import NovaResponseStreamHandler

"""
Stream parser for AWS Bedrock Nova model responses.

This module provides the NovaParsedEventStream class which orchestrates the parsing
of streaming responses from AWS Bedrock Nova models. It supports both invoke_model_with_response_stream
and converse streaming modes, and processes events to extract content between specified XML tags.

The class acts as a coordinator between NovaEventStream (which generates the output stream)
and NovaResponseStreamHandler (which processes individual chunks). It handles different
event types (messageStart, contentBlockDelta, messageStop, metadata) and routes them
appropriately.

Key features:
- Support for both invoke_model_with_response_stream and converse streaming modes
- XML tag-based content extraction
- Event-based processing with proper event routing
- Stream generation and management
"""

def parse_converse_stream(target_tag_name=None):
    """Python decorator that wraps stream processing functions"""
    def decorator(stream_func):
        def wrapper(*args, **kwargs):
            # Get the original stream from the function
            # args has the original stream
            original_stream = stream_func(*args, **kwargs)
            stream = NovaParsedEventStream()
            output_stream = stream.parse_converse_stream(target_tag_name)
            for event in original_stream:
                stream.add(event)
            # Wrap it with our parsing functionality
            return output_stream
        return wrapper
    return decorator

def parse_invoke_model_with_response_stream(target_tag_name=None):
    """Python decorator that wraps stream processing functions"""
    def decorator(stream_func):
        def wrapper(*args, **kwargs):
            # Get the original stream from the function
            # args has the original stream
            original_stream = stream_func(*args, **kwargs)
            stream = NovaParsedEventStream()
            output_stream = stream.parse_invoke_model_with_response_stream(target_tag_name)
            for event in original_stream:
                stream.add(event)
            # Wrap it with our parsing functionality
            return output_stream
        return wrapper
    return decorator

class NovaParsedEventStream:
    def __init__(self):
        self.target_tag_name = None
        self.generator = NovaEventStream()
        self.get_block = None
        self.stream_type = None
        self.handler = None
        
    def parse_converse_stream(self, target_tag_name):
        self.get_block = get_block_for_converse_streaming
        
        return self._parse(target_tag_name, CONVERSE_STREAM)
    
    def parse_invoke_model_with_response_stream(self, target_tag_name):
        self.get_block = get_block_for_invoke_model_with_response_stream

        return self._parse(target_tag_name, INVOKE_STREAM)
    
    def _parse(self, target_tag_name, stream_type):
        self.target_tag_name = target_tag_name
    
        self.stream = self.generator.generate_stream()
        self.stream_type = stream_type

        self.handler = NovaResponseStreamHandler(self.generator.add_event, self.stream_type)
        self.handler.set_target_tag_name(target_tag_name)

        return self.stream

    def add(self, event):
        if self.target_tag_name is None:
            raise ValueError("target_tag_name is not set")

        block = self.get_block(event)

        if block.get("messageStart") is not None:
            self.handler.on_start()
            self.generator.add_event(event)
        elif block.get("contentBlockDelta") is not None: # or payload_part_block.get("contentBlockStart") is not None:
            self.handler.on_chunk(event)
        elif block.get("messageStop") is not None:
            self.handler.on_end()
            self.generator.add_event(event)
        elif block.get("metadata") is not None:
            self.generator.add_event(event)
            self.generator.end_stream()
        else:
            self.generator.add_event(event)