import json

from typing import List
from .constants import INVOKE_STREAM, CONVERSE_STREAM
from .helpers import (
    get_block_for_invoke_model_with_response_stream, 
    get_block_for_converse_streaming,
    is_content_block_delta_valid,
    is_content_block_delta_text_valid,
    is_content_block_delta_tool_use_valid
)
from .nova_response_parser import NovaResponseParser

class NovaResponseStreamHandler:
    """
    Handler for processing streaming responses from AWS Bedrock Nova models.

    This module provides the NovaResponseStreamHandler class which processes and collates
    content chunks received from Nova LLM streaming responses. It supports both invoke_model_with_response_stream
    and converse streaming modes, handling text content and tool use blocks.

    The handler processes incoming chunks, extracts text and tool use information, and uses
    a NovaResponseParser to process text chunks and extract content between specified XML tags.
    Processed chunks are then passed to a callback function for further handling.

    Key features:
    - Support for different streaming modes (invoke_model and converse)
    - Processing of text content with XML tag extraction
    - Handling of tool use blocks
    - Event-based processing with callbacks
    - Stateful processing of streaming chunks
    """
    
    def __init__(self, on_chunk_callback, stream_type):
        self.tool_use_blocks: List = []
        self.thinking_text_builder: List[str] = []
        self.on_chunk_callback = on_chunk_callback
        
        self.serialized_tool_use_block_builder = None
        self.delta_block_builder = None
        self.content_delta_block_builder = None
        self.response_parser = None
        self.target_tag_name = None
        self.get_block = None

        if stream_type == INVOKE_STREAM:
            self.update_chunk_text = self._update_chunk_text_for_invoke_model_with_response_stream
            self.get_block = get_block_for_invoke_model_with_response_stream
        elif stream_type == CONVERSE_STREAM:
            self.update_chunk_text = self._update_chunk_text_for_converse_stream
            self.get_block = get_block_for_converse_streaming
        else:
            raise ValueError("Invalid stream_type")
        

    def set_target_tag_name(self, target_tag_name):
        self.target_tag_name = target_tag_name


    def on_start(self):
        if self.target_tag_name is None:
            raise ValueError("target_tag_name is not set")

        self.delta_block_builder = {}
        self.content_delta_block_builder = {}
        self.response_parser = NovaResponseParser(self.target_tag_name)


    def on_chunk(self, chunk):
        if chunk is None:
            raise ValueError("chunk cannot be None")

        block = self.get_block(chunk)

        if block is None:
            raise ValueError("block cannot be None")

        # check for a valid contentBlockDelta, but the function of this block is toolUse
        if is_content_block_delta_tool_use_valid(block):
                self._add(chunk)
        elif is_content_block_delta_valid(block) and is_content_block_delta_text_valid(block):
                text_response = block["contentBlockDelta"]["delta"]["text"]
                self.thinking_text_builder.append(text_response)
                
                new_chunk = self.response_parser.process_chunk(chunk, text_response, self.update_chunk_text)
            
                if new_chunk is not None:
                    self._add(new_chunk) 
        else: 
            self._add(chunk) 


    def on_end(self):
        self.response_parser = NovaResponseParser(self.target_tag_name)


    def _add(self, chunck):
        if self.response_parser is None:
            raise ValueError("response_parser is not set")
        
        self.on_chunk_callback(chunck)

    def _update_chunk_text_for_invoke_model_with_response_stream(self, chunk, text):
        if chunk is None:
            raise ValueError("chunk cannot be None")
        
        block = self.get_block(chunk)

        if block is None:
            raise ValueError("block cannot be None")
        
        block["contentBlockDelta"]["delta"]["text"] = text
        chunk["chunk"]["bytes"] = json.dumps(block).encode()
        return chunk
    
    def _update_chunk_text_for_converse_stream(self, chunk, text):
        if chunk is None:
            raise ValueError("chunk cannot be None")
        
        block = self.get_block(chunk)

        if block is None:
            raise ValueError("block cannot be None")
        
        if not is_content_block_delta_valid(block):
            raise ValueError("contentBlockDelta cannot be None")
        
        block["contentBlockDelta"]["delta"]["text"] = text
        return block