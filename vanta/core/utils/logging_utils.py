"""
Logging Utilities
Enhanced logging functionality for VANTA
"""

import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any


class ColoredFormatter(logging.Formatter):
    """Formatter that adds color to console logs"""
    
    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '\033[92m',   # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',   # Red
        'CRITICAL': '\033[91m\033[1m',  # Bold Red
        'RESET': '\033[0m'    # Reset
    }
    
    def format(self, record):
        """Format log record with colors"""
        log_message = super().format(record)
        levelname = record.levelname
        if levelname in self.COLORS:
            return f"{self.COLORS[levelname]}{log_message}{self.COLORS['RESET']}"
        return log_message


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    module_name: str = "vanta",
    config: Optional[Dict[str, Any]] = None
) -> logging.Logger:
    """
    Set up application logging with console and optional file output
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for no file logging)
        module_name: Name of the module for the logger
        config: Optional configuration dictionary that overrides other params
        
    Returns:
        Configured logger
    """
    # Apply config overrides if provided
    if config:
        log_level = config.get("system", {}).get("log_level", log_level)
        log_file = config.get("system", {}).get("log_file", log_file)
    
    # Create root logger and set level
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers from root logger
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # Create logger for our module
    logger = logging.getLogger(module_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with colored formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    root_logger.addHandler(console_handler)
    
    # Add file handler if log file specified
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        # Add to root logger to capture all logs
        root_logger.addHandler(file_handler)
    
    # Set specific module log levels
    
    # Enable DEBUG for VAD's important logs but filter other noise
    vad_logger = logging.getLogger("vanta.voice.listener.vad")
    vad_logger.setLevel(logging.INFO)  # Only show INFO and above for VAD
    
    # For microphone, we don't need constant audio level logs
    mic_logger = logging.getLogger("vanta.voice.listener.microphone")
    mic_logger.setLevel(logging.INFO)  # Only show INFO and above for microphone
    
    # Make sure STT logs are visible (transcription results)
    stt_logger = logging.getLogger("vanta.voice.listener.stt_service")
    stt_logger.setLevel(logging.INFO)
    
    # Make transcript processing visible
    transcript_logger = logging.getLogger("vanta.voice.listener.transcript_processor")
    transcript_logger.setLevel(logging.INFO)
    
    # Filter event bus spam
    event_bus_logger = logging.getLogger("vanta.core.event_bus")
    event_bus_logger.setLevel(logging.INFO)  # Hide DEBUG level event publishing
    
    return logger


class Timer:
    """Simple context manager for timing code blocks"""
    
    def __init__(self, name: str, logger: Optional[logging.Logger] = None):
        """
        Initialize timer
        
        Args:
            name: Name of the operation being timed
            logger: Logger to output to (None for no logging)
        """
        self.name = name
        self.logger = logger
        self.start_time = None
        
    def __enter__(self):
        """Start timing"""
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log result"""
        if self.start_time is None:
            return
            
        elapsed = time.time() - self.start_time
        
        if self.logger:
            self.logger.debug(f"{self.name} took {elapsed:.3f} seconds")
            
        return False  # Don't suppress exceptions