#!/usr/bin/env python3
'''
Whisper Worker Process

Runs in a separate process, receives audio data via stdin,
and returns transcription via stdout.

This worker script handles Whisper transcription in an isolated process
to prevent crashes from affecting the main application.
'''

import os
import sys
import json
import time
import logging
import traceback

# Configure logging to stderr to avoid interfering with IPC
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [WORKER] %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('whisper_worker')

def main():
    """Main worker process function"""
    # Parse command line arguments
    if len(sys.argv) < 3:
        logger.error("Usage: whisper_worker.py [model_name] [language] [max_memory_mb]")
        sys.exit(1)
    
    model_name = sys.argv[1]
    language = sys.argv[2]
    max_memory_mb = int(sys.argv[3]) if len(sys.argv) > 3 else 2048
    
    # Print startup message
    logger.info(f"Whisper worker starting with model: {model_name}, language: {language}")
    logger.info(f"Memory limit: {max_memory_mb}MB")
    
    # Try to set memory limits
    try:
        import resource
        # Convert MB to bytes
        mem_bytes = max_memory_mb * 1024 * 1024
        # Set memory limit (soft limit, can be exceeded temporarily)
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        logger.info(f"Memory limit set to {max_memory_mb}MB")
    except ImportError:
        logger.warning("resource module not available, cannot set memory limits")
    except Exception as e:
        logger.warning(f"Failed to set resource limits: {e}")
    
    # Import NumPy early to catch any errors
    try:
        import numpy as np
        logger.info("NumPy imported successfully")
    except ImportError:
        logger.error("NumPy not installed, cannot proceed")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Error importing NumPy: {e}")
        sys.exit(2)
    
    # Load Whisper
    model = None
    try:
        logger.info(f"Loading Whisper model: {model_name}")
        start_time = time.time()
        
        # Import Whisper
        import whisper
        
        # Load the model
        model = whisper.load_model(model_name)
        
        load_duration = time.time() - start_time
        logger.info(f"✅ Whisper model {model_name} loaded successfully in {load_duration:.2f}s")
    except ImportError:
        logger.error("Whisper not installed, cannot proceed")
        sys.exit(3)
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        logger.error(traceback.format_exc())
        sys.exit(3)
    
    # Process loop
    while True:
        try:
            # Read command from stdin (non-blocking)
            cmd_line = ""
            while True:
                if sys.stdin.isatty():
                    # Interactive mode for debugging
                    cmd_line = input("Enter command: ")
                    break
                else:
                    # Non-interactive mode (normal operation)
                    cmd_line = sys.stdin.readline().strip()
                    if cmd_line:
                        break
                    time.sleep(0.1)
            
            # Parse command
            cmd = json.loads(cmd_line)
            action = cmd.get('action')
            
            if action == 'exit':
                logger.info("Received exit command, shutting down")
                break
                
            elif action == 'transcribe':
                # Get audio data (base64 encoded)
                audio_b64 = cmd.get('audio')
                
                if not audio_b64:
                    logger.error("No audio data provided")
                    result = {'error': 'No audio data provided'}
                else:
                    try:
                        # Decode audio data from base64
                        import base64
                        audio_bytes = base64.b64decode(audio_b64)
                        
                        # Convert to numpy array (assuming float32)
                        import numpy as np
                        audio = np.frombuffer(audio_bytes, dtype=np.float32)
                        
                        # Get audio duration
                        sample_rate = cmd.get('sample_rate', 16000)
                        duration = len(audio) / sample_rate
                        
                        # Log audio info
                        logger.info(f"Transcribing audio: {duration:.2f}s, samples: {len(audio)}")
                        
                        # Transcribe with timing
                        start_time = time.time()
                        
                        result = model.transcribe(
                            audio,
                            language=language,
                            task="transcribe"
                        )
                        
                        process_duration = time.time() - start_time
                        logger.info(f"Transcription completed in {process_duration:.2f}s")
                        
                        # Extract text and create response
                        text = result.get('text', '').strip()
                        result = {
                            'text': text, 
                            'duration': process_duration,
                            'audio_duration': duration
                        }
                        
                        logger.info(f"Transcription result: '{text}'")
                    except Exception as e:
                        logger.error(f"Transcription error: {e}")
                        logger.error(traceback.format_exc())
                        result = {'error': str(e)}
                
                # Send result back through stdout
                output = json.dumps(result) + '\n'
                sys.stdout.write(output)
                sys.stdout.flush()
                
            elif action == 'ping':
                # Simple ping to check if the process is alive
                logger.info("Received ping command")
                result = {'status': 'ok', 'timestamp': time.time()}
                sys.stdout.write(json.dumps(result) + '\n')
                sys.stdout.flush()
                
            else:
                logger.warning(f"Unknown action: {action}")
                result = {'error': f'Unknown action: {action}'}
                sys.stdout.write(json.dumps(result) + '\n')
                sys.stdout.flush()
                
        except KeyboardInterrupt:
            logger.info("Interrupted, exiting...")
            break
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON command: {e}")
            if cmd_line:
                logger.error(f"Raw command: {cmd_line}")
            # Send error back
            error_result = {'error': 'Invalid JSON command'}
            sys.stdout.write(json.dumps(error_result) + '\n')
            sys.stdout.flush()
            
        except Exception as e:
            logger.error(f"Worker error: {e}")
            logger.error(traceback.format_exc())
            # Try to send error back
            try:
                error_result = {'error': f'Worker error: {str(e)}'}
                sys.stdout.write(json.dumps(error_result) + '\n')
                sys.stdout.flush()
            except:
                pass
    
    logger.info("Whisper worker exiting")
    sys.exit(0)

if __name__ == "__main__":
    main()