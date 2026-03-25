"""
Structured logging for Lambda functions.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """
    JSON structured log formatter for Lambda.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "function_name": os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "unknown"),
            "request_id": getattr(record, "aws_request_id", None),
        }

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class LambdaLogger(logging.Logger):
    """
    Custom logger with structured logging support.
    """

    def __init__(self, name: str, level: int = logging.INFO):
        super().__init__(name, level)
        self._aws_request_id: Optional[str] = None

    def set_request_id(self, request_id: str):
        """Set the AWS request ID for correlation."""
        self._aws_request_id = request_id

    def _log_with_context(
        self,
        level: int,
        msg: str,
        args: tuple = (),
        exc_info: Any = None,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Log with additional context."""
        if extra is None:
            extra = {}

        extra["aws_request_id"] = self._aws_request_id
        extra["extra"] = kwargs

        super()._log(level, msg, args, exc_info=exc_info, extra=extra)

    def info_with_context(self, msg: str, **kwargs):
        """Log info with context."""
        self._log_with_context(logging.INFO, msg, **kwargs)

    def warning_with_context(self, msg: str, **kwargs):
        """Log warning with context."""
        self._log_with_context(logging.WARNING, msg, **kwargs)

    def error_with_context(self, msg: str, exc_info: bool = False, **kwargs):
        """Log error with context."""
        self._log_with_context(logging.ERROR, msg, exc_info=exc_info, **kwargs)

    def debug_with_context(self, msg: str, **kwargs):
        """Log debug with context."""
        self._log_with_context(logging.DEBUG, msg, **kwargs)


# Global logger instance
_logger: Optional[LambdaLogger] = None


def setup_logger(name: str = "observability", level: Optional[int] = None) -> LambdaLogger:
    """
    Set up the structured logger.

    Args:
        name: Logger name
        level: Log level (defaults to INFO, or DEBUG if LAMBDA_DEBUG env var is set)

    Returns:
        Configured logger instance
    """
    global _logger

    if level is None:
        level = logging.DEBUG if os.environ.get("LAMBDA_DEBUG") else logging.INFO

    # Create logger
    logger = LambdaLogger(name, level)

    # Remove existing handlers
    logger.handlers = []

    # Add structured handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    _logger = logger
    return logger


def get_logger() -> LambdaLogger:
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger


def log_lambda_event(event: Dict[str, Any], context: Any):
    """
    Log Lambda invocation details.

    Call this at the start of each Lambda handler.
    """
    logger = get_logger()

    # Set request ID for correlation
    if context:
        logger.set_request_id(context.aws_request_id)

    # Log invocation
    logger.info_with_context(
        "Lambda invocation started",
        function_name=os.environ.get("AWS_LAMBDA_FUNCTION_NAME"),
        function_version=os.environ.get("AWS_LAMBDA_FUNCTION_VERSION"),
        memory_limit=os.environ.get("AWS_LAMBDA_FUNCTION_MEMORY_SIZE"),
        remaining_time_ms=context.get_remaining_time_in_millis() if context else None,
        event_source=_detect_event_source(event),
    )


def _detect_event_source(event: Dict[str, Any]) -> str:
    """Detect the source of the Lambda event."""
    if "Records" in event:
        if event["Records"] and "kinesis" in event["Records"][0]:
            return "kinesis"
        if event["Records"] and "Sns" in event["Records"][0]:
            return "sns"
        if event["Records"] and "s3" in event["Records"][0]:
            return "s3"
        if event["Records"] and "eventSource" in event["Records"][0]:
            return event["Records"][0]["eventSource"]
    if "requestContext" in event:
        if "http" in event.get("requestContext", {}):
            return "api_gateway_http"
        return "api_gateway"
    if "source" in event and event["source"].startswith("aws."):
        return "eventbridge"
    if "detail-type" in event:
        return "eventbridge"
    return "direct_invoke"
