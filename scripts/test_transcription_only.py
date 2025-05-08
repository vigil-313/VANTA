#!/usr/bin/env python3
"""
Simple transcription test script that captures audio and transcribes it directly.
This bypasses the event system to directly test the Whisper transcription.
"""

import numpy as np
import pyaudio
import time
import argparse
import sys
import os
import logging
import warnings
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("transcription_test")

# Suppress unnecessary warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Constants
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Must be 8000, 16000, 32000 or 48000 for WebRTC VAD
CHUNK = 480  # 30ms frames (480 samples at 16kHz)

# Try importing whisper
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.error("WHISPER NOT INSTALLED. Please install with: pip install -U openai-whisper")
    sys.exit(1)


class TranscriptionTest:
    def __init__(self, model_name="base", record_seconds=5):
        self.p = pyaudio.PyAudio()
        self.model_name = model_name
        self.whisper_model = None
        self.record_seconds = record_seconds
        self.stream = None
        
        # Load whisper model
        logger.info(f"Loading Whisper {model_name} model (this may take a moment)...")
        self.whisper_model = whisper.load_model(model_name)
        logger.info(f"Whisper {model_name} model loaded successfully!")
        
    def record_audio(self):
        """Record audio from microphone for a fixed duration"""
        frames = []
        
        # Open stream
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        logger.info(f"Recording {self.record_seconds} seconds of audio...")
        logger.info(f"Please speak now: 'Testing one two three. This is a voice recognition test.'")
        
        # Create a visual countdown
        for i in range(3, 0, -1):
            print(f"Starting in {i}...")
            time.sleep(1)
        
        print("🎙️ RECORDING NOW...")
        
        # Calculate how many chunks to record
        chunks_to_record = int((self.record_seconds * RATE) / CHUNK)
        
        # Record audio chunks
        for i in range(chunks_to_record):
            data = self.stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            # Show progress bar
            progress = (i / chunks_to_record) * 50
            sys.stdout.write("\r[" + "=" * int(progress) + " " * (50 - int(progress)) + f"] {i}/{chunks_to_record}")
            sys.stdout.flush()
            
        print("\n🛑 Recording complete!")
        
        # Close stream
        self.stream.stop_stream()
        self.stream.close()
        
        # Convert frames to numpy array
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        
        return audio_data
    
    def transcribe_audio(self, audio_data):
        """Transcribe audio using Whisper"""
        logger.info("🔊 Processing audio segment...")
        
        # Normalize audio for Whisper if needed
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
            
        # Start timer
        start_time = time.time()
        
        logger.info("🎯 Starting transcription with Whisper...")
        try:
            result = self.whisper_model.transcribe(
                audio_data,
                language="en",
                task="transcribe"
            )
            
            transcription = result.get("text", "").strip()
            duration = time.time() - start_time
            
            if transcription:
                logger.info(f"✅ TRANSCRIPTION COMPLETE!")
                print(f"\n{'=' * 60}")
                print(f"🔊 TRANSCRIPTION RESULT 🔊")
                print(f"{'=' * 60}")
                print(f"{transcription}")
                print(f"{'=' * 60}")
                print(f"Processing time: {duration:.2f} seconds")
            else:
                logger.warning(f"⚠️ Transcription returned empty result!")
                
            return transcription
        except Exception as e:
            logger.error(f"❌ Error transcribing speech: {e}")
            return None
    
    def run_test(self):
        """Run a complete test: record audio and transcribe it"""
        try:
            # Record audio
            audio_data = self.record_audio()
            
            # Transcribe the recorded audio
            transcription = self.transcribe_audio(audio_data)
            
            # Clean up
            self.p.terminate()
            
            return transcription
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        except Exception as e:
            logger.error(f"Error during test: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.p.terminate()


def main():
    parser = argparse.ArgumentParser(description="Test transcription with Whisper")
    parser.add_argument("--model", type=str, default="base", 
                        choices=["tiny", "base", "small", "medium"],
                        help="Whisper model to use for transcription")
    parser.add_argument("--duration", type=int, default=5,
                       help="Recording duration in seconds")
    
    args = parser.parse_args()
    
    try:
        test = TranscriptionTest(model_name=args.model, record_seconds=args.duration)
        test.run_test()
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())