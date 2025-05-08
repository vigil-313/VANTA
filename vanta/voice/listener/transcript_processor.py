"""
Transcript Processor
Processes speech transcriptions and manages conversation context
"""

import logging
import time
from typing import Dict, Any, List, Deque
from collections import deque

from vanta.core.event_bus import bus, EventType

logger = logging.getLogger(__name__)


class TranscriptEntry:
    """
    Represents a single transcript entry with timing information
    """
    
    def __init__(self, text: str, start_time: float, end_time: float, is_user: bool = True):
        """
        Initialize a transcript entry
        
        Args:
            text: Transcribed text
            start_time: Start timestamp
            end_time: End timestamp
            is_user: Whether this is from the user (True) or the system (False)
        """
        self.text = text
        self.start_time = start_time
        self.end_time = end_time
        self.is_user = is_user
        
    def __str__(self) -> str:
        speaker = "User" if self.is_user else "VANTA"
        return f"[{speaker} {time.strftime('%H:%M:%S', time.localtime(self.start_time))}] {self.text}"
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "is_user": self.is_user,
            "duration": self.end_time - self.start_time
        }


class TranscriptProcessor:
    """
    Processes transcriptions and maintains conversation context buffer
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the transcript processor
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.buffer_seconds = 60  # Keep 60 seconds of conversation
        self.context_buffer: Deque[TranscriptEntry] = deque()
        self.transcript_log_path = f"{config.get('system', {}).get('data_dir', 'data')}/conversations/transcript.log"
        
        # Create transcript log directory if it doesn't exist
        import os
        os.makedirs(os.path.dirname(self.transcript_log_path), exist_ok=True)
        
        logger.info(f"Transcript processor initialized with {self.buffer_seconds}s buffer")
    
    async def start(self):
        """Start the transcript processor"""
        logger.info("Starting transcript processor")
        
        # Subscribe to transcript events
        bus.subscribe(EventType.TRANSCRIPTION_COMPLETE, self.handle_transcription)
        bus.subscribe(EventType.SPEECH_COMPLETE, self.handle_system_speech)
    
    async def stop(self):
        """Stop the transcript processor"""
        logger.info("Stopping transcript processor")
    
    def handle_transcription(self, event_data: Dict[str, Any]):
        """
        Handle transcription event
        
        Args:
            event_data: Event data containing transcription
        """
        text = event_data.get("text", "")
        if not text.strip():
            return
            
        start_time = event_data.get("start_time", time.time())
        end_time = event_data.get("end_time", time.time())
        is_final = event_data.get("is_final", True)
        
        # Create and store the transcript entry
        entry = TranscriptEntry(text, start_time, end_time, is_user=True)
        self._add_to_buffer(entry)
        
        # Log to transcript file if final
        if is_final:
            self._log_transcript(entry)
        
        # If this is a final transcription, check if we should respond
        if is_final:
            # Build the context for decision making
            context_list = self._get_context_list()
            
            # Publish event for should_respond decision
            bus.publish(EventType.TRANSCRIPTION_PROCESSED, {
                "transcription": entry.to_dict(),
                "context": context_list,
                "buffer": [e.to_dict() for e in self.context_buffer]
            })
    
    def handle_system_speech(self, event_data: Dict[str, Any]):
        """
        Handle system speech completion event
        
        Args:
            event_data: Event data containing system speech details
        """
        text = event_data.get("text", "")
        if not text.strip():
            return
            
        start_time = event_data.get("start_time", time.time())
        end_time = event_data.get("end_time", time.time())
        
        # Create and store system transcript entry
        entry = TranscriptEntry(text, start_time, end_time, is_user=False)
        self._add_to_buffer(entry)
        self._log_transcript(entry)
    
    def _add_to_buffer(self, entry: TranscriptEntry):
        """
        Add entry to context buffer and prune older entries
        
        Args:
            entry: Transcript entry to add
        """
        self.context_buffer.append(entry)
        
        # Remove entries older than buffer_seconds
        current_time = time.time()
        while self.context_buffer and (current_time - self.context_buffer[0].start_time) > self.buffer_seconds:
            self.context_buffer.popleft()
    
    def _get_context_list(self) -> List[str]:
        """
        Get context buffer as a list of formatted strings
        
        Returns:
            List of formatted transcript entries
        """
        return [str(entry) for entry in self.context_buffer]
    
    def _log_transcript(self, entry: TranscriptEntry):
        """
        Log transcript entry to file
        
        Args:
            entry: Transcript entry to log
        """
        try:
            with open(self.transcript_log_path, "a", encoding="utf-8") as f:
                f.write(f"{str(entry)}\n")
        except Exception as e:
            logger.error(f"Error logging transcript: {e}")
            
    def get_buffer_for_should_respond(self) -> List[Dict[str, Any]]:
        """
        Get the current context buffer for should_respond decision
        
        Returns:
            List of transcript entries as dictionaries
        """
        return [entry.to_dict() for entry in self.context_buffer]