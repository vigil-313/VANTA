"""
Speech-to-Text Service
Transcribes audio to text using configured STT service
"""

import asyncio
import logging
import time
import os
from typing import Dict, Any, Optional, List, Tuple

from vanta.core.event_bus import bus, EventType
from vanta.core.utils.async_helpers import run_in_executor
from vanta.voice.listener.transcription_manager import TranscriptionManager

logger = logging.getLogger(__name__)

# These will be imported at runtime to avoid unnecessary dependencies
try:
    import numpy as np
except ImportError:
    logger.warning("numpy not installed - transcription functionality unavailable")


class STTService:
    """
    Speech-to-Text service that transcribes audio using the configured provider
    
    This service handles audio buffering and speech segments, then delegates
    the actual transcription to the TranscriptionManager which handles multiple
    backend services and fallbacks.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the STT service
        
        Args:
            config: STT configuration dictionary
        """
        self.config = config
        self.stt_config = config.get("stt", {})
        
        # Audio settings from microphone config
        mic_config = config.get("microphone", {})
        self.sample_rate = mic_config.get("sample_rate", 16000)
        
        # Audio buffer for the current speech segment
        self.current_audio_buffer = []
        self.speech_active = False
        self.segment_start_time = 0.0
        
        # Pending transcription queue to prevent overload
        self._pending_transcriptions = 0
        
        # Create transcription manager that handles multiple backends
        self.transcription_manager = TranscriptionManager(config)
        
        logger.info(f"STT service initialized")
    
    async def start(self):
        """Start the STT service"""
        logger.info("Starting STT service")
        
        # Subscribe to speech events
        bus.subscribe(EventType.SPEECH_DETECTED, self.handle_speech_detected)
        bus.subscribe(EventType.AUDIO_CAPTURED, self.handle_audio_captured)
        
        # Start the transcription manager
        await self.transcription_manager.start()
    
    async def stop(self):
        """Stop the STT service"""
        logger.info("Stopping STT service")
        
        # Processing any remaining audio in the buffer
        if self.speech_active and self.current_audio_buffer:
            await self.process_speech_segment(is_final=True)
            
        # Stop the transcription manager
        await self.transcription_manager.stop()
    
    def handle_speech_detected(self, event_data: Dict[str, Any]):
        """
        Handle speech detected event
        
        Args:
            event_data: Event data containing detection info
        """
        # Speech has started, reset buffer and record start time
        self.current_audio_buffer = []
        self.speech_active = True
        self.segment_start_time = event_data.get("timestamp", time.time())
        logger.debug(f"Speech segment started at {self.segment_start_time}")
    
    def handle_audio_captured(self, event_data: Dict[str, Any]):
        """
        Handle captured audio event
        
        Args:
            event_data: Event data containing audio samples
        """
        # Handle speech activation if not already active
        if not self.speech_active and event_data.get("is_speech", False):
            logger.info("STT detected speech activation from audio event")
            self.speech_active = True
            self.segment_start_time = event_data.get("timestamp", time.time())
            self.current_audio_buffer = []
        
        # If speech is not active, we don't need to process this audio
        if not self.speech_active:
            return
            
        # Get the audio data
        audio_data = event_data.get("audio_data")
        if audio_data is None:
            return
            
        # Add to buffer (only if speech is active)
        self.current_audio_buffer.append(audio_data.copy())
        
        # Log buffer growth periodically for debugging
        if len(self.current_audio_buffer) % 20 == 0:
            buffer_duration = len(self.current_audio_buffer) * (30/1000)  # Assuming 30ms frames
            logger.debug(f"Speech buffer growing: {len(self.current_audio_buffer)} chunks, ~{buffer_duration:.1f}s of audio")
        
        # If VAD indicates speech has ended, process the segment
        vad_state = self._get_vad_state(event_data)
        if vad_state.get("speech_ended", False):
            logger.info("💬 Speech ended detected by VAD, processing segment for transcription")
            asyncio.create_task(self.process_speech_segment(is_final=True))
            
        # Check if we've exceeded max duration (redundant failsafe)
        mic_config = self.config.get("microphone", {})
        max_duration_ms = mic_config.get("max_phrase_duration", 30000)
        current_duration_ms = (time.time() - self.segment_start_time) * 1000
        
        if current_duration_ms > max_duration_ms and self.current_audio_buffer:
            logger.info(f"⏱️ Max speech duration exceeded ({max_duration_ms/1000:.1f}s), forcing transcription")
            asyncio.create_task(self.process_speech_segment(is_final=True))
    
    def _get_vad_state(self, event_data: Dict[str, Any]) -> Dict[str, bool]:
        """Extract VAD state from event data if present"""
        return {
            "is_speech": event_data.get("is_speech", False),
            "speech_started": event_data.get("speech_started", False),
            "speech_ended": event_data.get("speech_ended", False)
        }
    
    async def process_speech_segment(self, is_final: bool = False):
        """
        Process the current speech segment
        
        Args:
            is_final: Whether this is the final segment of a speech
        """
        # Handle empty buffer case
        if not self.current_audio_buffer:
            if is_final:
                self.speech_active = False
                logger.warning("Empty audio buffer received for transcription, nothing to process")
            return
        
        # Limit concurrent transcriptions to prevent overload
        if self._pending_transcriptions > 2:
            logger.warning(f"⚠️ Too many pending transcriptions ({self._pending_transcriptions}), skipping this segment")
            if is_final:
                self.speech_active = False
                self.current_audio_buffer = []
            return
            
        # Make a local copy of the buffer to prevent race conditions
        buffer_to_process = list(self.current_audio_buffer)
        buffer_length = len(buffer_to_process)
            
        # Reset buffer and state BEFORE processing if final to allow new speech detection immediately
        if is_final:
            logger.debug(f"Resetting speech buffer and state (was {len(self.current_audio_buffer)} chunks)")
            self.current_audio_buffer = []
            self.speech_active = False
            
        # Combine audio chunks
        audio = self._combine_audio_chunks(buffer_to_process)
        segment_duration = len(audio) / self.sample_rate
        start_time = self.segment_start_time
        end_time = start_time + segment_duration
        
        # Log audio buffer stats for debugging
        logger.info(f"🔊 Processing speech segment: {buffer_length} chunks, {segment_duration:.2f}s duration")
        
        # Check if audio is too short
        if segment_duration < 0.3:  # Less than 300ms is too short for reliable transcription
            logger.warning(f"⚠️ Audio segment too short ({segment_duration:.2f}s), skipping transcription")
            return
        
        # Check if audio is too long - cap at 5 seconds to prevent Whisper from hanging
        MAX_DURATION = 5.0  # seconds
        if segment_duration > MAX_DURATION:
            logger.warning(f"⚠️ Audio segment too long ({segment_duration:.2f}s), truncating to {MAX_DURATION}s")
            # Truncate audio to first 5 seconds
            max_samples = int(MAX_DURATION * self.sample_rate)
            audio = audio[:max_samples]
            segment_duration = MAX_DURATION
            end_time = start_time + segment_duration
            
        # Track pending transcriptions
        self._pending_transcriptions += 1
        
        # Transcribe the audio
        try:
            logger.info("🎯 Starting transcription with Whisper...")
            
            # Start a timer for clear diagnostics
            import time
            transcription_start = time.time()
            
            # Use a lower timeout for very short segments for better responsiveness
            timeout = 5.0 if segment_duration < 1.0 else 10.0
            
            # Transcribe the audio with timeout
            transcription = await self._transcribe_audio(audio)
            
            # Calculate transcription time
            transcription_duration = time.time() - transcription_start
            logger.info(f"⏱️ Transcription took {transcription_duration:.2f}s for {segment_duration:.2f}s of audio")
            
            if transcription and transcription.strip():
                # Publish transcription event with very visible logging
                await bus.publish_async(EventType.TRANSCRIPTION_COMPLETE, {
                    "text": transcription,
                    "start_time": start_time,
                    "end_time": end_time,
                    "is_final": is_final,
                    "duration": segment_duration,
                    "confidence": 1.0  # Placeholder - Whisper doesn't provide confidence scores
                })
                
                # Add very clear logging with emoji markers for easy identification in logs
                logger.info(f"✅ TRANSCRIPTION COMPLETE: '{transcription}' ({segment_duration:.2f}s)")
                logger.info("=" * 50)
                logger.info(f"📝 TRANSCRIPT: {transcription}")
                logger.info("=" * 50)
            else:
                logger.warning(f"⚠️ Transcription returned empty result after processing {segment_duration:.2f}s of audio")
                logger.info(f"Audio duration: {segment_duration:.2f}s, Chunks: {buffer_length}")
        except Exception as e:
            logger.error(f"❌ Error transcribing speech segment ({segment_duration:.2f}s): {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # If transcription fails, ensure we reset state
            self.speech_active = False
        finally:
            # Always decrement pending count
            self._pending_transcriptions -= 1
    
    def _combine_audio_chunks(self, chunks: List[np.ndarray]) -> np.ndarray:
        """
        Combine audio chunks into a single array
        
        Args:
            chunks: List of audio chunks
            
        Returns:
            Combined audio as numpy array
        """
        import numpy as np
        return np.concatenate(chunks)
    
    async def _transcribe_audio(self, audio: np.ndarray) -> str:
        """
        Transcribe audio using the TranscriptionManager
        
        Args:
            audio: Audio data as numpy array
            
        Returns:
            Transcribed text
        """
        # Whisper expects float32 audio normalized between -1 and 1
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
            
        try:
            # Log details about the audio
            logger.info(f"🎯 Sending audio for transcription: shape={audio.shape}, dtype={audio.dtype}")
            
            # Use the transcription manager to handle all transcription
            transcription, metadata = await self.transcription_manager.transcribe(
                audio=audio,
                start_time=self.segment_start_time,
                end_time=self.segment_start_time + (len(audio) / self.sample_rate),
                is_final=True
            )
            
            # Log any errors in the metadata
            if "error" in metadata:
                logger.warning(f"⚠️ Transcription reported error: {metadata.get('error')}")
                
            return transcription
                
        except Exception as e:
            logger.error(f"❌ Error in transcription: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            try:
                logger.error(f"Audio info: shape={audio.shape}, dtype={audio.dtype}, min={audio.min():.4f}, max={audio.max():.4f}")
            except:
                logger.error("Failed to log audio info")
                
            return ""