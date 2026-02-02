"""Logging configuration for Ableton Hub."""

import logging
import sys
import os
import threading
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler

# Import LoggingConfig type hint (avoid circular import)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..config import LoggingConfig


def _is_development_mode() -> bool:
    """Check if running in development mode.
    
    Returns:
        True if running in development mode (__debug__ or ABLETON_HUB_DEBUG env var).
    """
    return __debug__ or os.getenv('ABLETON_HUB_DEBUG') == '1'


def get_logs_directory(config: Optional['LoggingConfig'] = None) -> Path:
    """Get the directory for log files.
    
    Args:
        config: Optional LoggingConfig. If provided and log_dir is set, use that.
                Otherwise, use default location.
    
    Returns:
        Path to logs directory.
    """
    if config and config.log_dir:
        log_dir = Path(config.log_dir)
    else:
        # Default: %APPDATA%/AbletonHub/logs
        from .paths import get_app_data_dir
        log_dir = get_app_data_dir() / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _get_log_level_from_string(level_str: str) -> int:
    """Convert log level string to logging constant.
    
    Args:
        level_str: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    
    Returns:
        Logging level constant.
    """
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    return level_map.get(level_str.upper(), logging.ERROR)


def setup_logging(
    config: Optional['LoggingConfig'] = None,
    log_level: Optional[int] = None,
    log_to_file: Optional[bool] = None
) -> None:
    """Configure application-wide logging.
    
    Args:
        config: Optional LoggingConfig. If provided, uses config values.
        log_level: Optional logging level (int). Overrides config if provided.
        log_to_file: Optional bool. Overrides config.enabled if provided.
    """
    # Determine log level
    if log_level is None:
        if config:
            log_level = _get_log_level_from_string(config.level)
        else:
            log_level = logging.ERROR  # Default to ERROR
    
    # Detect development mode and override if needed
    # Note: Dev mode override is handled in app.py, not here
    # This allows config to control level even in dev mode if explicitly set
    
    # Determine if file logging should be enabled
    if log_to_file is None:
        if config:
            log_to_file = config.enabled
        else:
            log_to_file = True  # Default: enabled
    
    # Create formatters
    # Standard formatter with timestamps and thread names
    standard_formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s:%(threadName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Detailed formatter for errors (includes traceback)
    error_formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s:%(threadName)s: %(message)s\n%(pathname)s:%(lineno)d',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(standard_formatter)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    
    # File handlers (if enabled)
    if log_to_file:
        logs_dir = get_logs_directory(config)
        
        # Main log file (all levels)
        main_log_path = logs_dir / "ableton_hub.log"
        max_bytes = config.max_bytes if config else 10 * 1024 * 1024  # 10MB
        backup_count = config.backup_count if config else 5
        
        file_handler = RotatingFileHandler(
            str(main_log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(standard_formatter)
        root_logger.addHandler(file_handler)
        
        # Error log file (ERROR and CRITICAL only)
        error_log_path = logs_dir / "ableton_hub_errors.log"
        error_handler = RotatingFileHandler(
            str(error_log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)  # Only ERROR and above
        error_handler.setFormatter(error_formatter)
        root_logger.addHandler(error_handler)
    
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
