"""Centralized logging configuration for the backend."""

import os
import logging


def setup_logging(log_file_name: str = "app.log") -> logging.Logger:
    """
    Configure logging to both console and file.

    Args:
        log_file_name: Name of the log file (default: app.log)

    Returns:
        Configured logger instance
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, log_file_name)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers = []

    # File handler - DEBUG level to capture everything
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)

    # Console handler - INFO level for normal operation
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

    # Set specific logger levels
    logging.getLogger("langgraph").setLevel(logging.DEBUG)

    return root_logger
