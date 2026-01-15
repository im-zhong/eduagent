"""Exception handlers for FastAPI API to catch and log all exceptions."""

from __future__ import annotations

from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from loguru import logger

from eduagent.logger import get_logger

api_exception_logger = get_logger(__name__, component="api.exception_handlers")


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for all unhandled exceptions.

    This handler will catch any exception that is not explicitly handled
    in the endpoints and log it with full context including:
    - Request method and path
    - Exception type and message
    - Full stack trace
    """
    # Log the full exception with traceback
    api_exception_logger.exception(
        "Unhandled exception in %s %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
    )

    # Return a user-friendly error response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please try again later.",
            "error_type": type(exc).__name__,
            "request": {
                "method": request.method,
                "path": request.url.path,
            },
        },
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle HTTPException to ensure they are also logged.
    """
    if hasattr(exc, "status_code") and hasattr(exc, "detail"):
        status_code = exc.status_code  # type: ignore[attr-defined]
        detail = exc.detail  # type: ignore[attr-defined]

        # Only log client errors at debug level, server errors at warning level
        if status_code >= 500:
            api_exception_logger.warning(
                "HTTP %d in %s %s: %s",
                status_code,
                request.method,
                request.url.path,
                detail,
            )
        else:
            api_exception_logger.debug(
                "HTTP %d in %s %s: %s",
                status_code,
                request.method,
                request.url.path,
                detail,
            )

        return JSONResponse(status_code=status_code, content={"detail": detail})

    # Fallback to global handler if not an HTTPException
    return await global_exception_handler(request, exc)


class EndpointLogger:
    """Helper class for logging endpoint execution."""

    def __init__(self, logger: Any, endpoint_name: str):
        self.logger = logger
        self.endpoint_name = endpoint_name

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log info message with endpoint context."""
        self.logger.info(f"[{self.endpoint_name}] {message}", *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message with endpoint context."""
        self.logger.debug(f"[{self.endpoint_name}] {message}", *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message with endpoint context."""
        self.logger.warning(f"[{self.endpoint_name}] {message}", *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log error message with endpoint context."""
        self.logger.error(f"[{self.endpoint_name}] {message}", *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback and endpoint context."""
        self.logger.exception(f"[{self.endpoint_name}] {message}", *args, **kwargs)
