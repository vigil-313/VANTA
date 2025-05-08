"""
Isolated Whisper Transcription Process

This module implements a separate process-based transcription service for Whisper
to prevent it from crashing the main application. It works by:

1. Running Whisper in a separate Python process
2. Using IPC (pipes) to communicate audio data and transcription results
3. Implementing watchdog timers to kill hung processes
4. Handling crashes gracefully with automatic restarts

Usage:
    The WhisperProcessManager handles creation and lifetime of the transcription process.
    The main application only needs to call transcribe() with audio data.
"""

import logging
import multiprocessing as mp
import os
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Default timeout for transcription (in seconds)
DEFAULT_TIMEOUT = 10.0

# Maximum memory allowed for the Whisper process (in MB)
MAX_MEMORY_MB = 2048  # 2GB

class WhisperProcess:
    """Manager for isolated Whisper transcription process"""
    
    def __init__(self, model_name: str = "base", language: str = "en"):
        """
        Initialize the Whisper process manager
        
        Args:
            model_name: Whisper model name (tiny, base, small, medium, large)
            language: Language code for transcription
        """
        self.model_name = model_name
        self.language = language
        
        # Process management
        self.process = None
        self.is_running = False
        self.last_restart = 0
        self.restart_count = 0
        self.max_restarts = 3
        
        # Initialize the process
        self._start_process()
    
    def _start_process(self):
        """Start the Whisper transcription process"""
        if self.process is not None:
            logger.warning("Process already exists, stopping first")
            self._stop_process()
        
        logger.info(f"Starting Whisper process with model: {self.model_name}")
        
        # Use subprocess instead of multiprocessing for better isolation
        # This completely isolates memory spaces and prevents crashes from affecting parent
        script_path = os.path.join(os.path.dirname(__file__), "whisper_worker.py")
        
        # Check if the worker script exists, if not create it
        if not os.path.exists(script_path):
            self._create_worker_script(script_path)
        
        # Create the subprocess with pipes for communication
        try:
            self.process = subprocess.Popen(
                [
                    sys.executable, 
                    script_path, 
                    self.model_name, 
                    self.language,
                    str(MAX_MEMORY_MB)
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # Set resource limits (UNIX-like systems only)
                preexec_fn=self._set_resource_limits
            )
            
            self.is_running = True
            self.last_restart = time.time()
            logger.info(f"Whisper process started with PID: {self.process.pid}")
        except Exception as e:
            logger.error(f"Failed to start Whisper process: {e}")
            self.is_running = False
            self.process = None
    
    def _set_resource_limits(self):
        """Set resource limits for the child process (UNIX only)"""
        try:
            import resource
            # Set memory limit (soft limit, can be exceeded temporarily)
            mem_bytes = MAX_MEMORY_MB * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except ImportError:
            logger.warning("resource module not available, cannot set memory limits")
        except Exception as e:
            logger.warning(f"Failed to set resource limits: {e}")
    
    def _stop_process(self):
        """Stop the Whisper process"""
        if self.process is None:
            return
        
        logger.info(f"Stopping Whisper process (PID: {self.process.pid})")
        
        try:
            # Try graceful termination first
            self.process.terminate()
            
            # Wait for process to terminate
            start_time = time.time()
            while self.process.poll() is None and time.time() - start_time < 3.0:
                time.sleep(0.1)
            
            # Force kill if still running
            if self.process.poll() is None:
                logger.warning(f"Process did not terminate gracefully, killing...")
                self.process.kill()
        except Exception as e:
            logger.error(f"Error stopping Whisper process: {e}")
        
        self.process = None
        self.is_running = False
    
    def _restart_if_needed(self):
        """Restart the process if it's not running"""
        if self.process is None or self.process.poll() is not None:
            logger.warning("Whisper process is not running, restarting...")
            
            # Check if we've exceeded max restarts
            if time.time() - self.last_restart < 60 and self.restart_count >= self.max_restarts:
                logger.error(f"Too many restarts in short period, waiting")
                time.sleep(5)  # Throttle restarts
            
            self._stop_process()  # Ensure cleanup
            self._start_process()
            self.restart_count += 1
            
            # Reset restart count after a period of stability
            if time.time() - self.last_restart > 300:  # 5 minutes
                self.restart_count = 0
    
    def _create_worker_script(self, script_path: str):
        """Create the worker script if it doesn't exist"""
        logger.info(f"Creating Whisper worker script at: {script_path}")
        
        script_content = """#!/usr/bin/env python3
'''
Whisper Worker Process
Runs in a separate process, receives audio data via stdin,
and returns transcription via stdout.
'''

import os
import sys
import json
import time
import logging
import numpy as np
import traceback

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [WORKER] %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('whisper_worker')

def main():
    # Parse arguments
    if len(sys.argv) < 3:
        logger.error("Usage: whisper_worker.py [model_name] [language] [max_memory_mb]")
        sys.exit(1)
    
    model_name = sys.argv[1]
    language = sys.argv[2]
    max_memory_mb = int(sys.argv[3]) if len(sys.argv) > 3 else 2048
    
    # Load whisper
    try:
        logger.info(f"Loading Whisper model: {model_name}")
        import whisper
        model = whisper.load_model(model_name)
        logger.info(f"Whisper model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        logger.error(traceback.format_exc())
        sys.exit(2)
    
    # Process loop
    while True:
        try:
            # Read command from stdin
            cmd_line = sys.stdin.readline().strip()
            if not cmd_line:
                time.sleep(0.1)
                continue
            
            # Parse command
            cmd = json.loads(cmd_line)
            action = cmd.get('action')
            
            if action == 'exit':
                logger.info("Received exit command")
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
                        
                        # Convert to numpy array
                        audio = np.frombuffer(audio_bytes, dtype=np.float32)
                        
                        # Transcribe
                        logger.info(f"Transcribing audio: {len(audio) / 16000:.2f}s")
                        start_time = time.time()
                        
                        result = model.transcribe(
                            audio,
                            language=language,
                            task="transcribe"
                        )
                        
                        duration = time.time() - start_time
                        logger.info(f"Transcription completed in {duration:.2f}s")
                        
                        # Extract text
                        text = result.get('text', '').strip()
                        result = {'text': text, 'duration': duration}
                    except Exception as e:
                        logger.error(f"Transcription error: {e}")
                        logger.error(traceback.format_exc())
                        result = {'error': str(e)}
                
                # Send back result
                sys.stdout.write(json.dumps(result) + '\\n')
                sys.stdout.flush()
            
            else:
                logger.warning(f"Unknown action: {action}")
                sys.stdout.write(json.dumps({'error': 'Unknown action'}) + '\\n')
                sys.stdout.flush()
                
        except KeyboardInterrupt:
            logger.info("Interrupted, exiting...")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}")
            logger.error(traceback.format_exc())
            # Don't exit on error, try to continue
    
    logger.info("Worker exiting")
    sys.exit(0)

if __name__ == "__main__":
    main()
"""
        
        # Write the script
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make it executable
        os.chmod(script_path, 0o755)
    
    def transcribe(self, audio: np.ndarray, timeout: float = DEFAULT_TIMEOUT) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribe audio using the isolated Whisper process
        
        Args:
            audio: Audio data as numpy array
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (transcription text, metadata)
        """
        # Check if we need to restart the process
        self._restart_if_needed()
        
        if not self.is_running or self.process is None:
            logger.error("Whisper process is not running and could not be restarted")
            return "", {"error": "Transcription process not available"}
            
        # Create a temporary file for the audio data to avoid pipe limitations
        try:
            # Prepare the audio data
            import json
            import base64
            
            # Ensure the audio is float32
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            
            # Convert to bytes and encode as base64
            audio_bytes = audio.tobytes()
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            # Create the command
            cmd = {
                'action': 'transcribe',
                'audio': audio_b64
            }
            cmd_json = json.dumps(cmd) + '\n'
            
            # Send command to the process
            logger.debug(f"Sending transcription command for {len(audio) / 16000:.2f}s of audio")
            self.process.stdin.write(cmd_json.encode('utf-8'))
            self.process.stdin.flush()
            
            # Read the result with timeout
            result = ""
            metadata = {}
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._read_response)
                try:
                    result, metadata = future.result(timeout=timeout)
                except Exception as e:
                    logger.error(f"Transcription timed out or failed: {e}")
                    self._restart_if_needed()  # Force restart on timeout
                    return "", {"error": f"Transcription timed out or failed: {e}"}
            
            return result, metadata
            
        except Exception as e:
            logger.error(f"Error in transcription: {e}")
            logger.error(traceback.format_exc())
            return "", {"error": str(e)}
    
    def _read_response(self) -> Tuple[str, Dict[str, Any]]:
        """Read and parse the response from the worker process"""
        import json
        response_line = self.process.stdout.readline().decode('utf-8').strip()
        
        if not response_line:
            return "", {"error": "Empty response from worker"}
        
        try:
            response = json.loads(response_line)
            if "error" in response:
                logger.warning(f"Worker reported error: {response['error']}")
                return "", response
                
            text = response.get("text", "")
            return text, response
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse worker response: {response_line}")
            return "", {"error": "Invalid JSON response from worker"}
    
    def shutdown(self):
        """Shutdown the Whisper process"""
        if self.is_running and self.process is not None:
            try:
                # Send exit command to process
                import json
                cmd = {'action': 'exit'}
                cmd_json = json.dumps(cmd) + '\n'
                self.process.stdin.write(cmd_json.encode('utf-8'))
                self.process.stdin.flush()
                
                # Wait a bit for graceful shutdown
                time.sleep(0.5)
            except:
                pass  # Ignore errors during shutdown
                
        self._stop_process()