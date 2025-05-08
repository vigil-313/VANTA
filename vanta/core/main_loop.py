"""
Main Loop
Orchestrates the overall VANTA system execution
"""

import asyncio
import logging
import signal
import time
import os
from typing import Dict, Any

from vanta.core.event_bus import bus, EventType
from vanta.core.system_status import SystemStatus

# Voice input components
from vanta.voice.listener.microphone import MicrophoneListener
from vanta.voice.listener.vad import VoiceActivityDetector
from vanta.voice.listener.stt_service import STTService
from vanta.voice.listener.transcript_processor import TranscriptProcessor

# Voice output components
from vanta.voice.speaker.tts_engine import TTSEngine
from vanta.voice.speaker.speech_queue import SpeechQueue

# Reasoning components
from vanta.reasoning.decision.speak_decider import SpeakDecider
from vanta.reasoning.decision.response_generator import ResponseGenerator

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
        
        # Create required directories
        self._ensure_directories()
        
        # Component references
        # Voice input
        self.microphone = None
        self.vad = None
        self.stt_service = None
        self.transcript_processor = None
        
        # Voice output
        self.tts_engine = None
        self.speech_queue = None
        
        # Reasoning
        self.speak_decider = None
        self.response_generator = None
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        data_dir = self.config.get("system", {}).get("data_dir", "data")
        log_dir = os.path.dirname(self.config.get("system", {}).get("log_file", "logs/vanta.log"))
        
        for directory in [data_dir, log_dir, f"{data_dir}/conversations", f"{data_dir}/vector_db"]:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
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
        
        # Initialize event bus first
        await bus.start()
        
        # Initialize voice input components
        self.microphone = MicrophoneListener(self.config)
        self.vad = VoiceActivityDetector(self.config)
        self.stt_service = STTService(self.config)
        self.transcript_processor = TranscriptProcessor(self.config)
        
        # Initialize reasoning components
        self.speak_decider = SpeakDecider(self.config)
        self.response_generator = ResponseGenerator(self.config)
        
        # Initialize voice output components
        self.tts_engine = TTSEngine(self.config)
        self.speech_queue = SpeechQueue(self.config)
        
        # Start components in correct order
        # 1. Start event handlers first
        await self.vad.start() if hasattr(self.vad, 'start') else None
        await self.stt_service.start()
        await self.transcript_processor.start()
        await self.speak_decider.start()
        await self.response_generator.start()
        await self.tts_engine.start()
        await self.speech_queue.start()
        
        # 2. Start data producers last (microphone should be last as it immediately starts producing data)
        await self.microphone.start()
        
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
        
        # Shutdown in reverse order
        # 1. Stop data producers first
        await self.microphone.stop()
        
        # 2. Stop other components
        await self.speech_queue.stop()
        await self.tts_engine.stop()
        await self.response_generator.stop()
        await self.speak_decider.stop()
        await self.transcript_processor.stop()
        await self.stt_service.stop()
        await self.vad.stop() if hasattr(self.vad, 'stop') else None
        
        # 3. Stop event bus last
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