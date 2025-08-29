#!/usr/bin/env python3
"""
Nova EventStream Generator - Creates event streams similar to using botocore.eventstream
"""

import time
from typing import Dict, Any, Iterator
from collections import deque


class NovaEventStream:
    """
    A class that generates event streams.
    This emmulates how AWS SDK handles event streaming.
    """
    
    def __init__(self):
        """
        Initialize the event stream generator.
        """
        self.event_count = 0
        self.event_queue = deque()
        self.close_stream = False
        self.callback = None
    
    def generate_stream(self) -> Iterator[Dict]:
        """
        Generate a stream of event dictionaries that mimic EventStreamMessage structure.
        Since we can't directly create EventStreamMessage objects (they require internal
        parameters), we'll return dictionaries with the same structure.
        
        Yields:
            Dict: Dictionary containing headers and payload similar to EventStreamMessage
        """
        while True:
            # Create event data
            if self.event_queue:
                event_data = self.event_queue.popleft()

                # Yield the message dictionary
                yield event_data
            
            # Allow threads to process
            time.sleep(0)
            
            if not self.event_queue and self.close_stream:
                break
    
    def add_event(self, event) -> Dict[str, Any]:
        self.event_queue.append(event)
    
    def end_stream(self):
        self._close_steam()

    def _close_steam(self):
        self.close_stream = True

