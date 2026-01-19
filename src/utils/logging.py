"""Logging configuration for Ableton Hub."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: int = logging.INFO,
    log_to_file: bool = False,
    log_file_path: Optional[Path] = None
) -> None:
    """Configure application-wide logging.
    
    Args:
        log_level: Logging level (default: INFO).
        log_to_file: Whether to write logs to a file.
        log_file_path: Optional custom path for log file.
    """
    # Create formatter
    formatter = logging.Formatter(
        fmt='[%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_to_file:
        if log_file_path is None:
            from .paths import get_config_path
            log_file_path = get_config_path().parent / "ableton_hub.log"
        
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress verbose logging from third-party libraries
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('PyQt6').setLevel(logging.WARNING)
    logging.getLogger('qt.multimedia').setLevel(logging.WARNING)
    logging.getLogger('qt.multimedia.ffmpeg').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__).
        
    Returns:
        Logger instance.
    """
    return logging.getLogger(name)
