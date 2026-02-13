"""
Enhanced Cognee - Standardized Logging Configuration

Provides consistent logging format throughout the codebase.
Replaces all print() statements with proper logger calls.

Log Format:
[LEVEL] [MODULE] Message

Levels:
DEBUG - Detailed diagnostic information
INFO - General informational messages
WARNING - Warning messages for potential issues
ERROR - Error messages for failures
CRITICAL - Critical messages for severe failures
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class EnhancedLogger:
    """
    Enhanced logger with consistent formatting.

    Replaces print() statements with structured logging.
    Provides ASCII-only output for Windows compatibility.
    """

    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialize enhanced logger.

        Args:
            name: Logger name (usually __name__)
            level: Logging level (default: INFO)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Remove any existing handlers
        self.logger.handlers.clear()

        # Create console handler with consistent format
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        # ASCII-only format (no Unicode symbols)
        formatter = logging.Formatter(
            '[%(levelname)-7s] [%(name)s] %(message)s'
        )
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def debug(self, msg: str, *args, **kwargs):
        """Log debug message."""
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """Log info message."""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """Log warning message."""
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """Log error message."""
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """Log critical message."""
        self.logger.critical(msg, *args, **kwargs)


def get_logger(name: str) -> EnhancedLogger:
    """
    Get or create an enhanced logger.

    Args:
        name: Logger name (use __name__ from calling module)

    Returns:
        EnhancedLogger instance
    """
    return EnhancedLogger(name)


def replace_print_with_logging():
    """
    Monkey-patch print() to use logger instead.

    This helps transition from print() to proper logging.
    Can be enabled for development/debugging.
    """
    import builtins

    original_print = builtins.print

    def enhanced_print(*args, **kwargs):
        """Enhanced print that logs instead."""
        msg = ' '.join(str(arg) for arg in args)
        logger = get_logger('print_replacement')
        logger.info(f"print() called: {msg}")

        # Still output to console
        original_print(*args, **kwargs)

    builtins.print = enhanced_print


def setup_logging(
    log_file: Optional[str] = None,
    log_level: str = "INFO",
    format_json: bool = False
) -> None:
    """
    Setup global logging configuration.

    Args:
        log_file: Optional log file path
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_json: Whether to format logs as JSON
    """
    # Convert log level string to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    level = level_map.get(log_level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=level,
        format='[%(levelname)-7s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)

        if format_json:
            import json
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                '[%(levelname)-7s] [%(name)s] %(message)s'
            )

        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)


# Example usage and testing
if __name__ == "__main__":
    # Test logger
    logger = get_logger(__name__)
    logger.info("Testing enhanced logging")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.debug("This is debug info")
    logger.critical("This is critical info")

    print("\nExample log output:")
    print("[INFO] [logging_config] Testing enhanced logging")
    print("[WARN] [logging_config] This is a warning message")
    print("[ERROR] [logging_config] This is an error message")
    print("[DEBUG] [logging_config] This is debug info")
    print("[CRITICAL] [logging_config] This is critical info")
