"""Structured logging configuration for ru-corrector service."""

import logging
import sys
import uuid
from contextvars import ContextVar

from .config import config

# Context variable to store request_id across async calls
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Add request_id to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "no-request-id"
        return True


def setup_logging() -> None:
    """
    Configure structured logging for the application.

    Note: This should only be called once at application startup.
    If logging is already configured, this function will reconfigure it.
    """
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(request_id)s | "
        "%(name)s:%(funcName)s:%(lineno)d | %(message)s"
    )

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Configure root logger
    root_logger = logging.getLogger()

    # Only reconfigure if not already configured, or force reconfiguration
    if not root_logger.handlers or root_logger.level == logging.NOTSET:
        root_logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))

        # Remove existing handlers to avoid duplicates
        root_logger.handlers.clear()

        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(RequestIdFilter())
        root_logger.addHandler(console_handler)

        # Reduce noise from third-party libraries
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("aiogram").setLevel(logging.INFO)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)


def set_request_id(request_id: str | None = None) -> str:
    """Set request_id in context and return it."""
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
