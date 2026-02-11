"""
Centralized logging configuration for HealthGuard backend.

This module provides:
- Multi-level logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Console output with colored formatting
- File output with JSON structured logging
- Rotating file handler to prevent disk space issues
- Sensitive data filtering
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to console output."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m',      # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add color to level name
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{level_color}{record.levelname:8s}{self.COLORS['RESET']}"

        # Format using parent formatter
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """Custom formatter to output structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(config: Any) -> None:
    """
    Setup logging configuration for the application.

    Args:
        config: Settings object with logging configuration
    """
    # Get root logger
    root_logger = logging.getLogger()

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Set log level from config
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Console handler with colored output
    if config.log_console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # Human-readable format for console
        console_format = (
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        console_formatter = ColoredFormatter(
            console_format,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # File handler with JSON formatting
    if config.log_file_enabled:
        # Create logs directory if it doesn't exist
        log_path = Path(config.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Rotating file handler (10MB per file, keep 5 backups)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=config.log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)

        # JSON format for file
        if config.log_json_format:
            file_formatter = JSONFormatter()
        else:
            # Plain text format as fallback
            file_format = (
                "%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
            )
            file_formatter = logging.Formatter(file_format, datefmt="%Y-%m-%d %H:%M:%S")

        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Set third-party library log levels to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Log initialization complete
    root_logger.info(
        f"Logging initialized: level={config.log_level.upper()}, "
        f"console={config.log_console_enabled}, "
        f"file={config.log_file_enabled}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the specified name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter to add contextual information to log records.

    Usage:
        logger = LoggerAdapter(logging.getLogger(__name__), {"user_id": "123"})
        logger.info("User action")  # Will include user_id in the log
    """

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add extra fields to the log record."""
        # Merge extra fields
        if 'extra' not in kwargs:
            kwargs['extra'] = {}

        kwargs['extra']['extra_fields'] = {**self.extra, **kwargs['extra'].get('extra_fields', {})}

        return msg, kwargs


def filter_sensitive_data(data: Any, sensitive_keys: Optional[list] = None) -> Any:
    """
    Filter sensitive information from log data.

    Args:
        data: Data to filter (dict, list, or primitive)
        sensitive_keys: List of keys to mask (default: password, token, secret, authorization)

    Returns:
        Filtered data with sensitive values replaced by "***FILTERED***"
    """
    if sensitive_keys is None:
        sensitive_keys = ['password', 'token', 'secret', 'authorization', 'api_key', 'api-key']

    if isinstance(data, dict):
        return {
            key: "***FILTERED***" if any(sensitive in key.lower() for sensitive in sensitive_keys)
            else filter_sensitive_data(value, sensitive_keys)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [filter_sensitive_data(item, sensitive_keys) for item in data]
    else:
        return data


def truncate_large_data(data: str, max_length: int = 5000) -> str:
    """
    Truncate large data to prevent huge logs.

    Args:
        data: String data to truncate
        max_length: Maximum length in characters (default: 5000)

    Returns:
        Truncated string with ellipsis if needed
    """
    if len(data) <= max_length:
        return data
    return data[:max_length] + f"... (truncated, total length: {len(data)})"
