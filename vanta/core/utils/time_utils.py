"""
Time Utilities
Time-related helper functions for VANTA
"""

import datetime
import time
from typing import Optional, Union, Tuple


def get_timestamp() -> float:
    """
    Get current timestamp
    
    Returns:
        Current time as float timestamp
    """
    return time.time()


def get_iso_timestamp() -> str:
    """
    Get current ISO 8601 formatted timestamp
    
    Returns:
        Current time in ISO format
    """
    return datetime.datetime.now().isoformat()


def format_timestamp(timestamp: Optional[float] = None,
                    format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a timestamp as a string
    
    Args:
        timestamp: Timestamp to format (None for current time)
        format_str: Format string
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = time.time()
        
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime(format_str)


def parse_timestamp(timestamp_str: str,
                   format_str: Optional[str] = None) -> float:
    """
    Parse a timestamp string to a float timestamp
    
    Args:
        timestamp_str: Timestamp string to parse
        format_str: Format string (None for auto-detect)
        
    Returns:
        Timestamp as float
    """
    if format_str:
        dt = datetime.datetime.strptime(timestamp_str, format_str)
    else:
        # Try ISO format first
        try:
            dt = datetime.datetime.fromisoformat(timestamp_str)
        except ValueError:
            # Try common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%m/%d/%Y %H:%M:%S",
                "%m/%d/%Y"
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.datetime.strptime(timestamp_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"Could not parse timestamp: {timestamp_str}")
                
    return dt.timestamp()


def get_time_parts() -> Tuple[int, int, int, int, int, int]:
    """
    Get current time broken into parts
    
    Returns:
        Tuple of (year, month, day, hour, minute, second)
    """
    now = datetime.datetime.now()
    return (now.year, now.month, now.day, now.hour, now.minute, now.second)


def time_since(timestamp: float) -> float:
    """
    Get seconds elapsed since a timestamp
    
    Args:
        timestamp: Reference timestamp
        
    Returns:
        Seconds elapsed since timestamp
    """
    return time.time() - timestamp


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds as a human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g. "2h 30m 45s")
    """
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    parts = []
    
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
        
    parts.append(f"{seconds}s")
    
    return " ".join(parts)