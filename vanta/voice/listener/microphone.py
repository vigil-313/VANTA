"""
Microphone Listener
Handles real-time audio capture from microphone
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional

from vanta.core.event_bus import bus, EventType
from vanta.core.utils.async_helpers import run_in_executor

logger = logging.getLogger(__name__)

# These will be imported at runtime to avoid unnecessary dependencies
# if the component isn't used
try:
    import numpy as np
    import sounddevice as sd
except ImportError:
    logger.warning("sounddevice not installed - microphone functionality unavailable")


class MicrophoneListener:
    """
    Captures real-time audio from microphone and emits audio events
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the microphone listener
        
        Args:
            config: Microphone configuration dictionary
        """
        self.config = config
        self.device_index = config.get("device_index")
        self.sample_rate = config.get("sample_rate", 16000)
        self.chunk_size = config.get("chunk_size", 1024)
        self.channels = config.get("channels", 1)
        
        self.running = False
        self.stream: Optional[Any] = None
        self._audio_task = None
    
    async def start(self):
        """Start listening for audio"""
        if self.running:
            return
            
        self.running = True
        logger.info("Starting microphone listener")
        
        try:
            # Import here to avoid errors if not used
            import sounddevice as sd
            import numpy as np
            
            # Start the audio processing task
            self._audio_task = asyncio.create_task(self._process_audio())
            
        except ImportError:
            logger.error("Failed to import audio libraries - microphone unavailable")
            self.running = False
    
    async def stop(self):
        """Stop listening for audio"""
        if not self.running:
            return
            
        logger.info("Stopping microphone listener")
        self.running = False
        
        if self._audio_task:
            self._audio_task.cancel()
            try:
                await self._audio_task
            except asyncio.CancelledError:
                pass
            self._audio_task = None
            
        if self.stream:
            await self._stop_stream()
    
    @run_in_executor
    def _stop_stream(self):
        """Stop the audio stream (runs in executor)"""
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error stopping audio stream: {e}")
            finally:
                self.stream = None
    
    def _audio_callback(self, indata, frames, time_info, status):
        """
        Callback function for audio data from sounddevice
        
        This runs in a separate thread managed by sounddevice
        """
        if status:
            logger.warning(f"Audio callback status: {status}")
            
        # Get the audio data as a numpy array
        audio_data = indata.copy()
        
        # Emit the audio data as an event
        timestamp = time.time()
        bus.publish(EventType.AUDIO_CAPTURED, {
            "audio_data": audio_data,
            "timestamp": timestamp,
            "sample_rate": self.sample_rate,
            "channels": self.channels
        })
    
    async def _process_audio(self):
        """Process audio stream (runs as async task)"""
        try:
            # Import here to avoid errors if not used
            import sounddevice as sd
            
            logger.info(f"Starting audio stream: {self.sample_rate}Hz, {self.channels} channels")
            
            # Start the audio stream
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                device=self.device_index,
                channels=self.channels,
                callback=self._audio_callback
            )
            
            with self.stream:
                logger.info("Audio stream started")
                # Keep the task alive while we're supposed to be running
                while self.running:
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            logger.exception(f"Error in audio processing: {e}")
            self.running = False
            
        finally:
            logger.info("Audio processing stopped")
            await self._stop_stream()