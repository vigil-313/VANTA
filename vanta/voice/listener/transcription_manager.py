"""
Transcription Manager

This module provides a centralized manager for speech transcription services.
It handles multiple transcription backends, fallbacks, and error recovery.
"""

import logging
import time
import traceback
from typing import Dict, Any, Optional, List, Tuple

import numpy as np

from vanta.core.event_bus import bus, EventType
from vanta.voice.listener import basic_stt
from vanta.voice.listener.whisper_process import WhisperProcess

logger = logging.getLogger(__name__)

class TranscriptionManager:
    """
    Manager for speech transcription services
    
    Coordinates between different transcription backends including:
    - Isolated Whisper process
    - Basic fallback transcription
    - (Future) Cloud-based services
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the transcription manager
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.stt_config = config.get("stt", {})
        
        # Service configuration
        self.primary_service = self.stt_config.get("service", "whisper")
        self.model_name = self.stt_config.get("model", "base")
        self.language = self.stt_config.get("language", "en")
        
        # Fallback configuration
        self.max_failures = self.stt_config.get("max_failures", 3)
        self.failure_backoff = self.stt_config.get("failure_backoff", 300)  # 5 minutes
        self.retry_delay = self.stt_config.get("retry_delay", 60)  # 1 minute
        
        # Timeouts
        self.timeout_short = self.stt_config.get("timeout_short", 5.0)
        self.timeout_standard = self.stt_config.get("timeout_standard", 10.0)
        
        # Audio settings from microphone config
        mic_config = config.get("microphone", {})
        self.sample_rate = mic_config.get("sample_rate", 16000)
        
        # Service instances
        self.whisper_process = None
        
        # State tracking
        self.failures = 0
        self.last_failure = 0
        self.last_retry = 0
        self.last_transcription = 0
        self.in_fallback_mode = False
        
        logger.info(f"Transcription manager initialized with primary service: {self.primary_service}")
    
    async def start(self):
        """Start the transcription manager"""
        logger.info("Starting transcription manager")
        
        # Initialize the primary service if it's Whisper
        if self.primary_service == "whisper":
            try:
                self.whisper_process = WhisperProcess(
                    model_name=self.model_name,
                    language=self.language
                )
                logger.info("Whisper process manager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Whisper process: {e}")
                logger.error(f"Falling back to basic transcription")
                self.in_fallback_mode = True
    
    async def stop(self):
        """Stop the transcription manager"""
        logger.info("Stopping transcription manager")
        
        # Shutdown Whisper process if running
        if self.whisper_process is not None:
            try:
                self.whisper_process.shutdown()
                logger.info("Whisper process shut down")
            except Exception as e:
                logger.error(f"Error shutting down Whisper process: {e}")
    
    async def transcribe(self, audio: np.ndarray, start_time: float, end_time: float, is_final: bool = True) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribe audio using the appropriate service based on current state
        
        Args:
            audio: Audio data as numpy array
            start_time: Start time of the audio segment
            end_time: End time of the audio segment
            is_final: Whether this is the final segment of a speech
            
        Returns:
            Tuple of (transcription text, metadata)
        """
        segment_duration = len(audio) / self.sample_rate
        logger.info(f"Transcribing audio segment: {segment_duration:.2f}s duration, is_final={is_final}")
        
        # Check if audio is too short
        if segment_duration < 0.3:  # Less than 300ms is too short for reliable transcription
            logger.warning(f"⚠️ Audio segment too short ({segment_duration:.2f}s), skipping transcription")
            return "", {"error": "Audio too short"}
        
        # Record transcription attempt
        self.last_transcription = time.time()
        
        # Check if we should try to recover from fallback mode
        if self.in_fallback_mode and time.time() - self.last_retry > self.retry_delay:
            await self._attempt_recovery()
            
        # Choose transcription method based on current state
        if self.in_fallback_mode or segment_duration < 0.5:
            # Use basic transcription for very short segments or when in fallback mode
            return await self._transcribe_with_basic(audio)
        else:
            # Use primary service (Whisper) with fallback
            try:
                transcription, metadata = await self._transcribe_with_primary(audio, segment_duration)
                
                if transcription or "error" not in metadata:
                    # Success, reset failure count
                    self.failures = 0
                    return transcription, metadata
                else:
                    # Primary service failed, increment failure count and try fallback
                    logger.warning(f"Primary transcription failed: {metadata.get('error')}")
                    await self._handle_failure()
                    return await self._transcribe_with_basic(audio)
                    
            except Exception as e:
                logger.error(f"Error in primary transcription: {e}")
                logger.error(traceback.format_exc())
                await self._handle_failure()
                return await self._transcribe_with_basic(audio)
    
    async def _transcribe_with_primary(self, audio: np.ndarray, segment_duration: float) -> Tuple[str, Dict[str, Any]]:
        """Transcribe using the primary service (Whisper)"""
        logger.info(f"🎯 Using primary transcription service (Whisper)")
        
        # For primary service, use shorter timeout for short segments
        timeout = self.timeout_short if segment_duration < 1.0 else self.timeout_standard
        
        if self.whisper_process is None:
            logger.error("Whisper process not initialized")
            return "", {"error": "Whisper process not initialized"}
        
        # Transcribe using the isolated process
        try:
            transcription, metadata = self.whisper_process.transcribe(audio, timeout=timeout)
            logger.info(f"✅ Whisper transcription complete: '{transcription}'")
            return transcription, metadata
        except Exception as e:
            logger.error(f"❌ Error in Whisper transcription: {e}")
            return "", {"error": str(e)}
    
    async def _transcribe_with_basic(self, audio: np.ndarray) -> Tuple[str, Dict[str, Any]]:
        """Transcribe using the basic fallback service"""
        logger.info(f"🔄 Using basic fallback transcription")
        try:
            result = basic_stt.simple_transcription(audio, self.sample_rate)
            return result, {"backend": "basic", "confidence": 0.5}
        except Exception as e:
            logger.error(f"❌ Error in basic transcription: {e}")
            return "", {"error": str(e)}
    
    async def _handle_failure(self):
        """Handle a transcription failure"""
        self.failures += 1
        self.last_failure = time.time()
        
        logger.warning(f"Transcription failure {self.failures}/{self.max_failures}")
        
        # If we've exceeded failure threshold, switch to fallback mode
        if self.failures >= self.max_failures:
            logger.error(f"Too many transcription failures, switching to fallback mode")
            self.in_fallback_mode = True
    
    async def _attempt_recovery(self):
        """Attempt to recover from fallback mode"""
        logger.info("Attempting to recover from fallback mode")
        self.last_retry = time.time()
        
        # If we're in fallback mode and it's been long enough, try to reinitialize
        if time.time() - self.last_failure < self.failure_backoff:
            logger.info(f"Not enough time has passed since last failure, staying in fallback mode")
            return
        
        # Try to reinitialize Whisper
        try:
            if self.whisper_process is not None:
                self.whisper_process.shutdown()
                
            self.whisper_process = WhisperProcess(
                model_name=self.model_name,
                language=self.language
            )
            
            logger.info("Successfully reinitialized Whisper process")
            self.failures = 0
            self.in_fallback_mode = False
        except Exception as e:
            logger.error(f"Failed to reinitialize Whisper process: {e}")
            logger.error(f"Remaining in fallback mode")
            # Reset failure count but stay in fallback
            self.failures = 0