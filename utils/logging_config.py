"""
Logging configuration for ChatDSJ Slack Bot.

This module configures the Loguru logger for the application.
"""
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from config.settings import get_settings


def configure_logging() -> logger:
    """
    Configure the Loguru logger based on application settings.
    
    This function:
    1. Removes the default handler
    2. Adds a stderr handler with appropriate formatting
    3. Adds a file handler in production environments
    
    Returns:
        logger: Configured Loguru logger instance
    """
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Add stderr handler
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    
    # Add file handler in production
    if settings.environment == "production":
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logger.add(
            log_dir / "chatdsj.log",
            level=settings.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="1 week",
        )
    
    logger.info(f"Logging configured with level {settings.log_level}")
    return logger