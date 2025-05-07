#!/usr/bin/env python3
"""
VANTA - Voice-based Ambient Neural Thought Assistant
Main entry point for the application
"""

import sys
import logging
from vanta.core.main_loop import MainLoop
from vanta.config.app_settings import load_config


def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/vanta.log")
        ]
    )


def main():
    """Application entry point"""
    setup_logging()
    logger = logging.getLogger("vanta")
    
    try:
        logger.info("Starting VANTA")
        config = load_config()
        loop = MainLoop(config)
        loop.run()
    except KeyboardInterrupt:
        logger.info("Shutting down VANTA")
    except Exception as e:
        logger.exception(f"Unhandled error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())