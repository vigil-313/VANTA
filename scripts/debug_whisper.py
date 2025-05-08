#!/usr/bin/env python3
"""
Debug script for testing Whisper transcription
"""

import sys
import os
import logging
import time
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def test_whisper():
    """Test Whisper transcription with a basic audio sample"""
    try:
        logger.info("Importing whisper...")
        import whisper
        
        logger.info("Loading model...")
        model = whisper.load_model("base")
        logger.info("Model loaded successfully")
        
        # Create a simple test audio array (1 second of silence)
        sample_rate = 16000
        audio = np.zeros(sample_rate, dtype=np.float32)
        
        logger.info("Starting transcription...")
        start_time = time.time()
        
        try:
            result = model.transcribe(
                audio,
                language="en",
                task="transcribe"
            )
            
            logger.info(f"Transcription complete in {time.time() - start_time:.2f} seconds")
            logger.info(f"Result: {result.get('text', '(empty)')}")
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    except ImportError as e:
        logger.error(f"Import error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    logger.info("Starting Whisper debug test")
    test_whisper()
    logger.info("Test completed")