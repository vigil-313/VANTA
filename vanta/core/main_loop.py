"""
Main Loop
Orchestrates the overall VANTA system execution
"""

import asyncio
import logging
import signal
import time
from typing import Dict, Any

from vanta.core.event_bus import bus, EventType
from vanta.core.system_status import SystemStatus
from vanta.voice.listener.microphone import MicrophoneListener
from vanta.voice.speaker.speech_queue import SpeechQueue

logger = logging.getLogger(__name__)


class MainLoop:
    """
    Main application control loop that coordinates all VANTA components
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the main loop
        
        Args:
            config: Application configuration dictionary
        """
        self.config = config
        self.running = False
        self.system_status = SystemStatus()
        
        # Component references
        self.microphone = None
        self.speech_queue = None
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handle_shutdown_signal)
    
    def _handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown")
        self.running = False
    
    async def _initialize_components(self):
        """Initialize and connect all system components"""
        logger.info("Initializing system components")
        
        # Initialize event bus
        await bus.start()
        
        # Initialize voice components
        self.microphone = MicrophoneListener(self.config.get("microphone", {}))
        self.speech_queue = SpeechQueue(self.config.get("speaker", {}))
        
        # Initialize other components here as they're implemented
        # ...
        
        # Publish system startup event
        await bus.publish_async(EventType.SYSTEM_STARTUP, {
            "timestamp": time.time(),
            "config": self.config
        })
        
        logger.info("All components initialized")
    
    async def _shutdown_components(self):
        """Gracefully shut down all components"""
        logger.info("Shutting down system components")
        
        # Publish shutdown event
        await bus.publish_async(EventType.SYSTEM_SHUTDOWN, {
            "timestamp": time.time()
        })
        
        # Shutdown voice components
        if self.microphone:
            await self.microphone.stop()
        
        if self.speech_queue:
            await self.speech_queue.stop()
            
        # Shutdown other components here as they're implemented
        # ...
        
        # Stop event bus last
        await bus.stop()
        
        logger.info("All components shut down")
    
    async def _run_async(self):
        """Async implementation of the main loop"""
        try:
            await self._initialize_components()
            
            logger.info("VANTA system is running")
            self.system_status.set_ready()
            
            # Main loop
            while self.running:
                # Most processing happens through the event bus
                # This loop just keeps the program alive and handles any
                # periodic tasks that aren't event-driven
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.exception(f"Error in main loop: {e}")
        finally:
            await self._shutdown_components()
    
    def run(self):
        """Run the main application loop"""
        logger.info("Starting main loop")
        self._setup_signal_handlers()
        self.running = True
        self.system_status.set_starting()
        
        # Run the async loop
        asyncio.run(self._run_async())