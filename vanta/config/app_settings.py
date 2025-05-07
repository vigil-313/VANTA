"""
App Settings
Configuration loader and manager for VANTA
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "default_config.yaml")
USER_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".vanta", "config.yaml")


def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    Load a YAML configuration file
    
    Args:
        file_path: Path to YAML file
        
    Returns:
        Configuration dictionary
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"Config file not found: {file_path}")
            return {}
    except Exception as e:
        logger.error(f"Error loading config file {file_path}: {e}")
        return {}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with override taking precedence
    
    Args:
        base: Base dictionary
        override: Override dictionary with higher precedence
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
            
    return result


def load_config(custom_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from default and user files
    
    Args:
        custom_path: Optional path to a custom config file
        
    Returns:
        Merged configuration dictionary
    """
    # Load default config
    config = load_yaml(DEFAULT_CONFIG_PATH)
    
    # Merge with user config if exists
    if os.path.exists(USER_CONFIG_PATH):
        user_config = load_yaml(USER_CONFIG_PATH)
        config = deep_merge(config, user_config)
    
    # Merge with custom config if provided
    if custom_path and os.path.exists(custom_path):
        custom_config = load_yaml(custom_path)
        config = deep_merge(config, custom_config)
    
    # Apply environment variable overrides
    apply_env_overrides(config)
    
    return config


def apply_env_overrides(config: Dict[str, Any]):
    """
    Apply environment variable overrides to configuration
    
    Environment variables should be in the format:
    VANTA_SECTION_KEY=value
    
    For example:
    VANTA_SYSTEM_LOG_LEVEL=DEBUG
    
    Args:
        config: Configuration dictionary to update in-place
    """
    prefix = "VANTA_"
    
    for env_key, env_value in os.environ.items():
        if env_key.startswith(prefix):
            # Strip prefix and split by underscore
            key_parts = env_key[len(prefix):].lower().split("_")
            
            # Navigate to the correct nested dictionary
            current = config
            for part in key_parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the value
            last_key = key_parts[-1]
            
            # Try to convert to the appropriate type
            if env_value.lower() == "true":
                current[last_key] = True
            elif env_value.lower() == "false":
                current[last_key] = False
            elif env_value.isdigit():
                current[last_key] = int(env_value)
            elif env_value.replace(".", "", 1).isdigit():
                current[last_key] = float(env_value)
            else:
                current[last_key] = env_value


def save_user_config(config: Dict[str, Any]) -> bool:
    """
    Save configuration to user config file
    
    Args:
        config: Configuration dictionary to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(USER_CONFIG_PATH), exist_ok=True)
        
        # Write config
        with open(USER_CONFIG_PATH, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        return True
    except Exception as e:
        logger.error(f"Error saving user config: {e}")
        return False