"""
Voice Activity Detection
Detects voice activity in audio streams

IMPORTANT: Calibrated for systems with low microphone input levels.
See comments throughout this file for detailed information about calibration
and threshold settings.
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
    Detects voice activity in audio streams using WebRTC VAD and amplitude thresholds
    
    This implementation uses a dual-detection approach:
    1. WebRTC VAD for speech detection
    2. Amplitude thresholds as a backup detection mechanism
    
    This combination works well for systems with low microphone input levels where
    the WebRTC VAD algorithm alone might miss speech. Calibrated based on diagnostic
    testing that showed typical speech levels between 0.001-0.01 with peaks up to 0.18.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the VAD
        
        Args:
            config: VAD configuration dictionary
        """
        self.config = config
        
        # WebRTC VAD settings - use well balanced mode by default
        # 0 = least aggressive (more false positives but catches more actual speech)
        # 3 = most aggressive (fewer false positives but might miss some speech)
        self.sensitivity = 2  # Hardcoded to mode 2 for better filtering
        
        # Frame settings
        self.frame_duration_ms = 30  # WebRTC VAD works with 10, 20, or 30 ms frames
        self.silence_threshold_ms = 500  # 500ms of silence to trigger speech end
        
        # Speech state tracking
        self.speech_active = False
        self.silent_frames = 0
        self.consecutive_speech_frames = 0
        self.min_speech_frames = 5  # Require 5 frames (~150ms) to trigger speech
        
        # Amplitude threshold - calibrated based on our testing
        # Based on diagnostic testing that showed typical speech levels between 0.001-0.01
        self.audio_threshold = 0.003  # Hardcoded to 0.003 based on observed levels
        
        # WebRTC VAD instance (initialized on demand)
        self._vad = None
        
        # Running state
        self.running = False
        
        # Max speech duration before forced end (in frames)
        # ~4.5 seconds at 30ms per frame = 150 frames
        self.max_speech_frames = 150  # Hardcoded to 150 frames
        
        # Max silence frames before ending speech (calculated from ms)
        self.max_silence_frames = int(self.silence_threshold_ms / self.frame_duration_ms)

        logger.info(f"VAD initialized with WebRTC sensitivity {self.sensitivity}, amplitude threshold {self.audio_threshold}, silence frames {self.max_silence_frames}")
    
    def _get_vad(self):
        """Get or initialize the VAD instance"""
        if self._vad is None:
            try:
                import webrtcvad
                self._vad = webrtcvad.Vad()
                self._vad.set_mode(self.sensitivity)
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
        
    async def start(self):
        """Start the VAD and subscribe to audio events"""
        if self.running:
            return
            
        self.running = True
        
        # Initialize VAD
        self._get_vad()
        
        # Subscribe to audio events
        bus.subscribe(EventType.AUDIO_CAPTURED, self.handle_audio_event)
        logger.info("VAD started and subscribed to audio events")
    
    async def stop(self):
        """Stop the VAD and unsubscribe from audio events"""
        if not self.running:
            return
            
        self.running = False
        
        # Unsubscribe from audio events
        bus.unsubscribe(EventType.AUDIO_CAPTURED, self.handle_audio_event)
        logger.info("VAD stopped")
    
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
                
                # Calculate audio level (RMS amplitude)
                audio_level = np.sqrt(np.mean(np.square(audio_data.astype(np.float32) / 32767.0)))
                
                # More selective logging to reduce noise
                # Only log when speech is detected by VAD or when level is significant
                if (is_speech and audio_level > self.audio_threshold) or audio_level > 0.01:
                    logger.debug(f"VAD processing audio with level: {audio_level:.6f}, VAD detected speech: {is_speech}")
                
                # More strict amplitude threshold detection 
                volume_is_speech = audio_level > self.audio_threshold
                
                # With VAD mode 2, we should usually require both detections to align
                # But we'll still allow WebRTC VAD alone if it's very confident
                if self.sensitivity >= 2:
                    # In more aggressive modes, require both OR very strong amplitude
                    combined_is_speech = (is_speech and volume_is_speech) or (audio_level > self.audio_threshold * 3)
                else:
                    # In less aggressive modes, allow either detection method
                    combined_is_speech = is_speech or volume_is_speech
                
                # Handle state transitions
                if combined_is_speech:
                    self.consecutive_speech_frames += 1
                    self.silent_frames = 0
                    
                    # Only mark as speech after several consecutive speech frames
                    if self.consecutive_speech_frames >= self.min_speech_frames:
                        # Transition from non-speech to speech
                        if not self.speech_active:
                            self.speech_active = True
                            speech_started = True
                            logger.info(f"Speech started (audio level: {audio_level:.6f}, VAD: {is_speech}, Volume: {volume_is_speech})")
                        speech_detected = True
                        if self.consecutive_speech_frames % 10 == 0:  # Log every 10 frames during speech
                            logger.debug(f"Speech continues, frames: {self.consecutive_speech_frames}")
                else:
                    self.consecutive_speech_frames = 0
                    
                    if self.speech_active:
                        self.silent_frames += 1
                        
                        # Log silence for debugging
                        if self.silent_frames % 5 == 0:  # Log every 5 frames
                            logger.debug(f"Silence during speech, frames: {self.silent_frames}/{self.max_silence_frames}")
                        
                        # Enough silence to mark end of speech
                        if self.silent_frames >= self.max_silence_frames:
                            self.speech_active = False
                            speech_ended = True
                            logger.info(f"🛑 NATURAL SILENCE DETECTED: Speech ended after {self.silent_frames} silent frames ({self.silent_frames * self.frame_duration_ms}ms)")
                            # Reset state
                            self.silent_frames = 0
                            self.consecutive_speech_frames = 0
            
        except Exception as e:
            logger.error(f"Error processing audio for VAD: {e}")
            
        return speech_detected, speech_started, speech_ended
    
    def handle_audio_event(self, event_data: Dict[str, Any]):
        """
        Handle audio captured event
        
        Args:
            event_data: Event data containing audio_data and metadata
        """
        if not self.running:
            return
        
        audio_data = event_data.get("audio_data")
        sample_rate = event_data.get("sample_rate", 16000)
        timestamp = event_data.get("timestamp")
        audio_level = event_data.get("audio_level", 0.0)
        
        if audio_data is None:
            return
        
        # Only log significant audio levels for debugging
        if audio_level > 0.01:
            logger.debug(f"VAD received audio with level: {audio_level:.6f}")
            
        # Process any non-zero audio (crucial for systems with low mic levels)
        if audio_level < 0.0001:  # Only skip completely silent audio
            return
            
        # Process audio for voice activity
        is_speech, speech_started, speech_ended = self.process_audio(audio_data, sample_rate)
        
        # Emit speech events as needed
        if speech_started:
            # IMPORTANT: Let's be very clear in logs when we detect speech
            logger.info(f"🎙️ SPEECH DETECTED! Publishing SPEECH_DETECTED event (level: {audio_level:.6f})")
            bus.publish(EventType.SPEECH_DETECTED, {
                "timestamp": timestamp,
                "sample_rate": sample_rate,
                "audio_level": audio_level
            })
            
        # Also include speech state in every audio captured event while speech is active
        if self.speech_active:
            event_data["is_speech"] = True
            
        # Handle speech ending
        if speech_ended:
            logger.info("🛑 SPEECH ENDED, sending for transcription")
            # Make sure to include speech_ended in the audio event so STT knows to process it
            event_data["speech_ended"] = True
            
            # Publish a special SPEECH_COMPLETE event as well
            bus.publish(EventType.SPEECH_COMPLETE, {
                "timestamp": timestamp,
                "duration": (self.silent_frames * self.frame_duration_ms) / 1000.0,
                "sample_rate": sample_rate
            })
        
        # Force transcription if the speech has been active for a long time
        # Check if speech has been active for more than the max allowed duration
        if self.speech_active and self.consecutive_speech_frames >= self.max_speech_frames:
            logger.info(f"🛑 LONG SPEECH DETECTED ({self.consecutive_speech_frames * self.frame_duration_ms / 1000:.1f}s), forcing transcription")
            
            # Set speech_ended flag to trigger transcription
            event_data["speech_ended"] = True
            
            # Reset speech state
            self.speech_active = False
            duration = (self.consecutive_speech_frames * self.frame_duration_ms) / 1000.0
            self.consecutive_speech_frames = 0
            self.silent_frames = 0
            
            # Publish a special SPEECH_COMPLETE event as well for the transcript processor
            bus.publish(EventType.SPEECH_COMPLETE, {
                "timestamp": timestamp,
                "duration": duration,
                "sample_rate": sample_rate,
                "forced": True  # Flag that this was a forced completion
            })
            
        # Forcibly detect speech for debugging if level is very high
        if audio_level > 0.05 and not self.speech_active:
            logger.warning(f"⚠️ HIGH AUDIO LEVEL DETECTED: {audio_level:.6f} but speech not active! Check VAD sensitivity.")