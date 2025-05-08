#!/usr/bin/env python3
"""
Debug script for testing Whisper transcription with timeout protection
"""

import sys
import os
import logging
import time
import signal
import numpy as np
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Set a signal handler to catch timeouts
class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Whisper transcription timeout")

def run_with_timeout(func, *args, timeout=30, **kwargs):
    """Run a function with a timeout"""
    # Set up the alarm
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    try:
        result = func(*args, **kwargs)
        return result
    except TimeoutException:
        logger.error(f"Function timed out after {timeout} seconds")
        return None
    finally:
        # Cancel the alarm
        signal.alarm(0)

def transcribe_with_whisper(audio, timeout=30):
    """Transcribe audio with a timeout"""
    try:
        import whisper
        model = whisper.load_model("base")
        
        logger.info(f"Starting transcription with shape={audio.shape}")
        start_time = time.time()
        
        # Run transcription with timeout
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(model.transcribe, audio, language="en", task="transcribe")
                result = future.result(timeout=timeout)
                
            elapsed = time.time() - start_time
            logger.info(f"Transcription completed in {elapsed:.2f}s")
            return result.get("text", "").strip()
        except TimeoutError:
            logger.error(f"Transcription timed out after {timeout}s")
            return ""
        
    except Exception as e:
        logger.error(f"Error in transcription: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return ""

def test_whisper():
    """Test Whisper transcription with a basic audio sample"""
    try:
        logger.info("Loading audio data...")
        
        # Create a simple test audio array (1 second of silence)
        sample_rate = 16000
        audio = np.zeros(sample_rate, dtype=np.float32)
        
        # Add a small amount of noise to make it more realistic
        noise = np.random.normal(0, 0.001, sample_rate)
        audio += noise
        
        logger.info(f"Audio ready: shape={audio.shape}, dtype={audio.dtype}")
        logger.info(f"Audio stats: min={audio.min():.6f}, max={audio.max():.6f}")
        
        logger.info("Starting transcription with timeout protection...")
        result = transcribe_with_whisper(audio, timeout=10)
        
        if result:
            logger.info(f"Transcription result: '{result}'")
        else:
            logger.warning("No transcription result")
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    logger.info("Starting Whisper debug test with timeout protection")
    test_whisper()
    logger.info("Test completed")