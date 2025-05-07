"""
Voice Activity Detection
Detects voice activity in audio streams
"""

import logging
import numpy as np
from typing import Dict, Any, Optional, Tuple

from vanta.core.event_bus import bus, EventType

logger = logging.getLogger(__name__)

# These will be imported at runtime to avoid unnecessary dependencies
# if the component isn't used
try:
    import webrtcvad
except ImportError:
    logger.warning("webrtcvad not installed - VAD functionality unavailable")


class VoiceActivityDetector:
    """
    Detects voice activity in audio streams using WebRTC VAD
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the VAD
        
        Args:
            config: VAD configuration dictionary
        """
        self.config = config
        self.sensitivity = config.get("vad_sensitivity", 3)  # 1-3, 3 is most sensitive
        self.frame_duration_ms = 30  # WebRTC VAD works with 10, 20, or 30 ms frames
        self.silence_threshold_ms = config.get("silence_threshold", 400)
        self.speech_active = False
        self.silent_frames = 0
        
        # WebRTC VAD instance (initialized on demand)
        self._vad = None
        
        # State tracking
        self.consecutive_speech_frames = 0
        self.min_speech_frames = 3  # Require N consecutive speech frames to trigger speech
        
        logger.info(f"VAD initialized with sensitivity {self.sensitivity}")
    
    def _get_vad(self):
        """Get or initialize the VAD instance"""
        if self._vad is None:
            try:
                import webrtcvad
                self._vad = webrtcvad.Vad(self.sensitivity)
                logger.debug(f"WebRTC VAD created with mode {self.sensitivity}")
            except ImportError:
                logger.error("Cannot initialize VAD: webrtcvad not installed")
                return None
        return self._vad
    
    def reset_state(self):
        """Reset the VAD state"""
        self.speech_active = False
        self.silent_frames = 0
        self.consecutive_speech_frames = 0
    
    def process_audio(self, audio_data: np.ndarray, sample_rate: int) -> Tuple[bool, bool, bool]:
        """
        Process audio data to detect voice activity
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of the audio
            
        Returns:
            Tuple of (is_speech, speech_start, speech_end)
        """
        vad = self._get_vad()
        if vad is None:
            return False, False, False
            
        # Convert float audio to int16 if needed
        if audio_data.dtype != np.int16:
            audio_data = (audio_data * 32767).astype(np.int16)
            
        # Get frame size in samples
        frame_size = int(sample_rate * self.frame_duration_ms / 1000)
        
        # Process audio frame by frame
        speech_detected = False
        speech_started = False
        speech_ended = False
        
        try:
            # WebRTC VAD only accepts 16-bit mono PCM audio
            # Ensure we have the right number of samples for a VAD frame
            if len(audio_data) >= frame_size:
                frame_bytes = audio_data[:frame_size].tobytes()
                is_speech = vad.is_speech(frame_bytes, sample_rate)
                
                # Handle state transitions
                if is_speech:
                    self.consecutive_speech_frames += 1
                    self.silent_frames = 0
                    
                    # Only mark as speech after several consecutive speech frames
                    if self.consecutive_speech_frames >= self.min_speech_frames:
                        # Transition from non-speech to speech
                        if not self.speech_active:
                            self.speech_active = True
                            speech_started = True
                            logger.debug("Speech started")
                        speech_detected = True
                else:
                    self.consecutive_speech_frames = 0
                    
                    if self.speech_active:
                        self.silent_frames += 1
                        
                        # Enough silence to mark end of speech
                        silence_frames = int(self.silence_threshold_ms / self.frame_duration_ms)
                        if self.silent_frames >= silence_frames:
                            self.speech_active = False
                            speech_ended = True
                            logger.debug("Speech ended")
            
        except Exception as e:
            logger.error(f"Error processing audio for VAD: {e}")
            
        return speech_detected, speech_started, speech_ended
    
    def handle_audio_event(self, event_data: Dict[str, Any]):
        """
        Handle audio captured event
        
        Args:
            event_data: Event data containing audio_data and metadata
        """
        audio_data = event_data.get("audio_data")
        sample_rate = event_data.get("sample_rate", 16000)
        timestamp = event_data.get("timestamp")
        
        if audio_data is None:
            return
            
        # Process audio for voice activity
        is_speech, speech_started, speech_ended = self.process_audio(audio_data, sample_rate)
        
        # Emit speech events as needed
        if speech_started:
            bus.publish(EventType.SPEECH_DETECTED, {
                "timestamp": timestamp,
                "sample_rate": sample_rate
            })
            
        # Additional logic for continuous speech and speech end events can be added here