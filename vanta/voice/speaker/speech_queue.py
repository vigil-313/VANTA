"""
Speech Queue
Manages speech output queue to prevent overlapping responses
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from collections import deque

from vanta.core.event_bus import bus, EventType

logger = logging.getLogger(__name__)


class SpeechQueue:
    """
    Manages the speech output queue to ensure responses
    are spoken in order without overlapping
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the speech queue
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.queue = asyncio.Queue()
        self.is_speaking = False
        self.current_item = None
        self._processing_task = None
        
        logger.info("Speech queue initialized")
    
    async def start(self):
        """Start the speech queue processor"""
        logger.info("Starting speech queue")
        
        # Subscribe to speak text events
        bus.subscribe(EventType.SPEAK_TEXT, self.handle_speak_text)
        bus.subscribe(EventType.SPEECH_COMPLETE, self.handle_speech_complete)
        
        # Start the queue processing task
        self._processing_task = asyncio.create_task(self._process_queue())
    
    async def stop(self):
        """Stop the speech queue processor"""
        logger.info("Stopping speech queue")
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
    
    def handle_speak_text(self, event_data: Dict[str, Any]):
        """
        Handle speak text event
        
        Args:
            event_data: Event data containing text to speak
        """
        # Add to queue
        self.queue.put_nowait(event_data)
        logger.debug(f"Added text to speech queue: '{event_data.get('text', '')[:30]}...'")
    
    def handle_speech_complete(self, event_data: Dict[str, Any]):
        """
        Handle speech complete event
        
        Args:
            event_data: Event data from speech completion
        """
        # Update speaking state
        self.is_speaking = event_data.get("is_speaking", False)
        
        # If this is the completion of our current item, mark it as done
        if not self.is_speaking and self.current_item:
            text = event_data.get("text", "")
            current_text = self.current_item.get("text", "")
            
            if text == current_text:
                self.current_item = None
                logger.debug(f"Completed speech: '{text[:30]}...'")
    
    async def _process_queue(self):
        """Process the speech queue"""
        logger.debug("Speech queue processor started")
        
        while True:
            try:
                # Wait for an item and mark as current
                self.current_item = await self.queue.get()
                
                # Check if we need to wait for previous speech to complete
                while self.is_speaking:
                    await asyncio.sleep(0.1)
                
                # Forward to TTS engine via event bus
                text = self.current_item.get("text", "")
                if text.strip():
                    logger.info(f"Speaking: '{text}'")
                    # Set state before sending to avoid race conditions
                    self.is_speaking = True
                    
                    # Forward the event
                    await bus.publish_async(EventType.SPEAK_TEXT, self.current_item)
                
                # Mark task as done
                self.queue.task_done()
                
                # Delay between items if needed
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                logger.debug("Speech queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in speech queue processor: {e}")
                
        logger.debug("Speech queue processor stopped")