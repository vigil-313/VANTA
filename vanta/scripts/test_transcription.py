#!/usr/bin/env python3
"""
Transcription Component Test Script

This script tests the new transcription architecture with a focus on:
1. Isolated Whisper process functionality
2. Transcription Manager fallback mechanisms
3. Basic STT functionality
4. End-to-end transcription flow

Usage:
    python test_transcription.py [--verbose] [--audio-file PATH]
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from typing import Dict, Any, Optional

import numpy as np

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from vanta.voice.listener.basic_stt import simple_transcription
from vanta.voice.listener.whisper_process import WhisperProcess
from vanta.voice.listener.transcription_manager import TranscriptionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("transcription_test.log")
    ]
)
logger = logging.getLogger("transcription_test")


async def test_whisper_process():
    """Test the isolated Whisper process"""
    logger.info("=== Testing WhisperProcess ===")
    
    wp = WhisperProcess(model_name="base", language="en")
    logger.info(f"WhisperProcess created with PID: {wp.process.pid}")
    
    # Create test audio (silent with some sine waves)
    sample_rate = 16000
    audio = np.zeros(sample_rate * 2, dtype=np.float32)  # 2 seconds
    
    # Add a simple 1-second sine wave at 400Hz
    t = np.linspace(0, 1, sample_rate)
    audio[sample_rate//2:sample_rate//2 + sample_rate] = np.sin(2 * np.pi * 400 * t) * 0.5
    
    logger.info(f"Transcribing test audio ({len(audio)/sample_rate:.1f}s)")
    start_time = time.time()
    
    # Transcribe with the WhisperProcess
    try:
        transcription, metadata = wp.transcribe(audio, timeout=15.0)
        duration = time.time() - start_time
        
        logger.info(f"Transcription completed in {duration:.2f}s")
        logger.info(f"Transcription: '{transcription}'")
        logger.info(f"Metadata: {metadata}")
        
        if transcription:
            logger.info("✅ WhisperProcess test PASSED")
        else:
            logger.warning("⚠️ WhisperProcess returned empty transcription")
    except Exception as e:
        logger.error(f"❌ WhisperProcess test FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Test with empty audio (should handle gracefully)
    logger.info("Testing with empty audio (should return empty string)")
    empty_audio = np.zeros(100, dtype=np.float32)
    try:
        result, meta = wp.transcribe(empty_audio)
        logger.info(f"Empty audio result: '{result}', metadata: {meta}")
    except Exception as e:
        logger.error(f"Error with empty audio: {e}")
    
    # Clean up
    logger.info("Shutting down WhisperProcess")
    wp.shutdown()


async def test_basic_stt():
    """Test the basic fallback STT"""
    logger.info("=== Testing Basic STT ===")
    
    # Create test audio of different lengths
    sample_rate = 16000
    
    # Short audio (0.3s)
    short_audio = np.zeros(int(sample_rate * 0.3), dtype=np.float32)
    short_audio[:] = np.sin(np.linspace(0, 10 * np.pi, len(short_audio))) * 0.5
    
    # Medium audio (1.2s)
    medium_audio = np.zeros(int(sample_rate * 1.2), dtype=np.float32)
    medium_audio[:] = np.sin(np.linspace(0, 40 * np.pi, len(medium_audio))) * 0.5
    
    # Long audio (3s)
    long_audio = np.zeros(int(sample_rate * 3), dtype=np.float32)
    long_audio[:] = np.sin(np.linspace(0, 100 * np.pi, len(long_audio))) * 0.5
    
    # Test with each audio length
    logger.info("Testing short audio (0.3s)")
    short_result = simple_transcription(short_audio, sample_rate)
    logger.info(f"Short audio result: '{short_result}'")
    
    logger.info("Testing medium audio (1.2s)")
    medium_result = simple_transcription(medium_audio, sample_rate)
    logger.info(f"Medium audio result: '{medium_result}'")
    
    logger.info("Testing long audio (3s)")
    long_result = simple_transcription(long_audio, sample_rate)
    logger.info(f"Long audio result: '{long_result}'")
    
    logger.info("✅ Basic STT test completed")


async def test_transcription_manager():
    """Test the TranscriptionManager with fallback behavior"""
    logger.info("=== Testing TranscriptionManager ===")
    
    # Create configuration
    config = {
        "stt": {
            "service": "whisper",
            "model": "base",
            "language": "en",
            "max_failures": 2,
            "failure_backoff": 10,  # Short for testing
            "retry_delay": 5       # Short for testing
        },
        "microphone": {
            "sample_rate": 16000
        }
    }
    
    # Create TranscriptionManager
    tm = TranscriptionManager(config)
    await tm.start()
    logger.info("TranscriptionManager started")
    
    # Create test audio
    sample_rate = 16000
    audio = np.zeros(sample_rate * 2, dtype=np.float32)  # 2 seconds
    
    # Add a simple 1-second sine wave
    t = np.linspace(0, 1, sample_rate)
    audio[sample_rate//2:sample_rate//2 + sample_rate] = np.sin(2 * np.pi * 400 * t) * 0.5
    
    # Test normal transcription
    logger.info("Testing normal transcription path")
    start_time = time.time()
    text, metadata = await tm.transcribe(audio, start_time, start_time + 2.0)
    duration = time.time() - start_time
    
    logger.info(f"Transcription completed in {duration:.2f}s")
    logger.info(f"Transcription: '{text}'")
    logger.info(f"Metadata: {metadata}")
    
    # Test fallback behavior by simulating failures
    # Force fallback mode
    logger.info("Testing fallback behavior by forcing failures")
    tm.failures = tm.max_failures
    tm.in_fallback_mode = True
    
    # Transcribe again (should use fallback)
    logger.info("Transcribing with fallback mode active")
    start_time = time.time()
    fallback_text, fallback_metadata = await tm.transcribe(audio, start_time, start_time + 2.0)
    duration = time.time() - start_time
    
    logger.info(f"Fallback transcription completed in {duration:.2f}s")
    logger.info(f"Fallback transcription: '{fallback_text}'")
    logger.info(f"Fallback metadata: {fallback_metadata}")
    
    # Test recovery attempt
    logger.info("Testing recovery from fallback mode")
    tm.last_failure = time.time() - tm.failure_backoff - 10  # Set failure time in the past
    tm.last_retry = time.time() - tm.retry_delay - 10  # Set retry time in the past
    
    # Trigger recovery attempt
    recovery_text, recovery_metadata = await tm.transcribe(audio, start_time, start_time + 2.0)
    
    logger.info(f"After recovery attempt, in_fallback_mode: {tm.in_fallback_mode}")
    logger.info(f"Recovery transcription: '{recovery_text}'")
    
    # Clean up
    await tm.stop()
    logger.info("TranscriptionManager stopped")
    logger.info("✅ TranscriptionManager test completed")


async def load_audio_file(file_path: str) -> Optional[np.ndarray]:
    """Load audio from a file for testing"""
    try:
        logger.info(f"Loading audio file: {file_path}")
        
        # Check file existence
        if not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            return None
            
        # Try to load with various libraries
        try:
            import soundfile as sf
            audio, sample_rate = sf.read(file_path)
            logger.info(f"Loaded with soundfile: {len(audio)} samples, {sample_rate}Hz")
            return audio.astype(np.float32)
        except ImportError:
            logger.warning("soundfile not available, trying scipy")
            
        try:
            from scipy.io import wavfile
            sample_rate, audio = wavfile.read(file_path)
            logger.info(f"Loaded with scipy: {len(audio)} samples, {sample_rate}Hz")
            
            # Convert to float32 in range [-1, 1]
            if audio.dtype == np.int16:
                audio = audio.astype(np.float32) / 32768.0
            elif audio.dtype == np.int32:
                audio = audio.astype(np.float32) / 2147483648.0
                
            return audio
        except ImportError:
            logger.error("Neither soundfile nor scipy available")
            return None
            
    except Exception as e:
        logger.error(f"Error loading audio file: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


async def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="Test the transcription components")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--audio-file", "-a", type=str, help="Path to audio file for testing")
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    logger.info("Starting transcription component tests")
    
    # Load audio file if provided
    test_audio = None
    if args.audio_file:
        test_audio = await load_audio_file(args.audio_file)
    
    try:
        # Run the tests
        await test_basic_stt()
        await test_whisper_process()
        await test_transcription_manager()
        
        logger.info("All tests completed")
        
    except Exception as e:
        logger.error(f"Error in tests: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
        
    return 0


if __name__ == "__main__":
    # Run the async main function
    result = asyncio.run(main())
    sys.exit(result)