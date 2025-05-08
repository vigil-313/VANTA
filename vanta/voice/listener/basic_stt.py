"""
Basic STT Service
A simplified fallback transcription service that doesn't rely on Whisper
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

def is_silence(audio: np.ndarray, threshold: float = 0.01) -> bool:
    """Check if audio is mostly silence"""
    rms = np.sqrt(np.mean(np.square(audio)))
    return rms < threshold

def detect_speech_content(audio: np.ndarray) -> bool:
    """
    Detect if there's actual speech content in the audio
    This is a simple heuristic based on audio variance and amplitude
    """
    # Check if audio is mostly silence
    if is_silence(audio):
        return False
    
    # Check for dynamic range (speech has more variation than background noise)
    normalized = audio / (np.max(np.abs(audio)) + 1e-10)
    std_dev = np.std(normalized)
    return std_dev > 0.05

def estimate_speech_duration(audio: np.ndarray, sample_rate: int = 16000) -> float:
    """Estimate speech duration in seconds"""
    # Simple amplitude-based voice activity detection
    frames = np.array_split(audio, max(1, len(audio) // 1000))
    active_frames = 0
    
    for frame in frames:
        if np.max(np.abs(frame)) > 0.01:  # Simple threshold
            active_frames += 1
            
    active_duration = active_frames * (len(audio) / len(frames)) / sample_rate
    return active_duration

def simple_transcription(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """
    A very basic transcription placeholder that doesn't actually transcribe
    but provides feedback about the audio without using Whisper
    """
    if audio is None or len(audio) < sample_rate * 0.2:  # Less than 200ms
        return ""
    
    # Check if there's speech content
    has_speech = detect_speech_content(audio)
    if not has_speech:
        return ""
    
    # Estimate speech duration
    duration = estimate_speech_duration(audio, sample_rate)
    
    # For short speech segments, return a generic response
    if duration < 0.5:
        return "..."
        
    elif duration < 1.0:
        return "... short phrase ..."
        
    elif duration < 2.0:
        return "... sentence ..."
        
    else:
        return "... longer speech ..."
    
    return ""