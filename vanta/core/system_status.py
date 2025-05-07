"""
System Status
Tracks the overall state of the VANTA system
"""

import logging
import time
from enum import Enum, auto
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SystemState(Enum):
    """System operational states"""
    INITIALIZING = auto()
    STARTING = auto()
    READY = auto()
    PROCESSING = auto()
    SPEAKING = auto()
    ERROR = auto()
    SHUTTING_DOWN = auto()
    SHUTDOWN = auto()


class SystemStatus:
    """
    Manages and reports on the overall state of the VANTA system
    """
    
    def __init__(self):
        """Initialize the system status tracker"""
        self._state = SystemState.INITIALIZING
        self._state_changed_at = time.time()
        self._last_activity = time.time()
        self._error = None
        self._metrics = {
            "transcriptions": 0,
            "responses": 0,
            "errors": 0,
            "uptime_start": time.time()
        }
    
    @property
    def state(self) -> SystemState:
        """Current system state"""
        return self._state
    
    @property
    def uptime(self) -> float:
        """System uptime in seconds"""
        return time.time() - self._metrics["uptime_start"]
    
    @property
    def time_in_state(self) -> float:
        """Time in current state in seconds"""
        return time.time() - self._state_changed_at
    
    @property
    def idle_time(self) -> float:
        """Time since last activity in seconds"""
        return time.time() - self._last_activity
    
    @property
    def metrics(self) -> Dict[str, Any]:
        """System metrics dictionary"""
        return {
            **self._metrics,
            "uptime": self.uptime,
            "current_state": self._state.name,
            "time_in_state": self.time_in_state,
            "idle_time": self.idle_time
        }
    
    @property
    def last_error(self) -> Optional[str]:
        """Last error message if any"""
        return self._error
    
    def set_state(self, state: SystemState):
        """
        Set the system state
        
        Args:
            state: New system state
        """
        if state == self._state:
            return
            
        logger.info(f"System state changing: {self._state.name} → {state.name}")
        self._state = state
        self._state_changed_at = time.time()
        self._last_activity = time.time()
        
        if state == SystemState.ERROR:
            self._metrics["errors"] += 1
    
    def set_error(self, error_msg: str):
        """
        Set system to error state with message
        
        Args:
            error_msg: Error description
        """
        logger.error(f"System error: {error_msg}")
        self._error = error_msg
        self.set_state(SystemState.ERROR)
    
    def set_initializing(self):
        """Set system to initializing state"""
        self.set_state(SystemState.INITIALIZING)
    
    def set_starting(self):
        """Set system to starting state"""
        self.set_state(SystemState.STARTING)
    
    def set_ready(self):
        """Set system to ready state"""
        self.set_state(SystemState.READY)
    
    def set_processing(self):
        """Set system to processing state"""
        self.set_state(SystemState.PROCESSING)
    
    def set_speaking(self):
        """Set system to speaking state"""
        self.set_state(SystemState.SPEAKING)
        self._metrics["responses"] += 1
    
    def set_shutting_down(self):
        """Set system to shutting down state"""
        self.set_state(SystemState.SHUTTING_DOWN)
    
    def set_shutdown(self):
        """Set system to shutdown state"""
        self.set_state(SystemState.SHUTDOWN)
    
    def increment_transcription(self):
        """Increment transcription counter"""
        self._metrics["transcriptions"] += 1
        self._last_activity = time.time()
    
    def report(self) -> Dict[str, Any]:
        """Generate status report"""
        return {
            "state": self._state.name,
            "uptime": self.uptime,
            "idle_time": self.idle_time,
            "metrics": self.metrics,
            "error": self._error
        }