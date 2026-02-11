"""
FastAPI middleware for logging API requests and responses.

Uses pure ASGI middleware (not BaseHTTPMiddleware) for compatibility
with StreamingResponse and other async response types.

This middleware automatically logs:
- Request: method, path, query params, headers, body
- Response: status code, processing time
- Filters sensitive data (tokens, passwords)
"""

import json
import logging
import time
from typing import Optional
from starlette.types import ASGIApp, Receive, Scope, Send

from ..core.logging_config import filter_sensitive_data, truncate_large_data

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Pure ASGI middleware to log all API requests and responses."""

    def __init__(self, app: ASGIApp, exclude_paths: Optional[list] = None):
        """
        Initialize the logging middleware.

        Args:
            app: The ASGI application
            exclude_paths: List of paths to exclude from verbose logging (e.g., ["/health"])
        """
        self.app = app
        self.exclude_paths = exclude_paths or ["/health", "/"]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI entry point."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip verbose logging for excluded paths
        if path in self.exclude_paths:
            await self.app(scope, receive, send)
            return

        # Record start time
        start_time = time.time()

        # Extract request details from scope
        request_id = id(scope)
        method = scope.get("method", "UNKNOWN")
        query_string = scope.get("query_string", b"").decode("utf-8", errors="ignore")
        query_params = dict(
            item.split("=", 1) for item in query_string.split("&") if "=" in item
        ) if query_string else None

        # Extract headers
        headers_raw = scope.get("headers", [])
        headers_dict = {
            k.decode("utf-8", errors="ignore"): v.decode("utf-8", errors="ignore")
            for k, v in headers_raw
        }
        client = scope.get("client")
        client_host = client[0] if client else None
        user_agent = headers_dict.get("user-agent")

        # Cache body from receive for logging (pass-through to downstream)
        body_chunks = []
        body_complete = False

        async def logging_receive():
            nonlocal body_complete
            message = await receive()
            if message["type"] == "http.request" and not body_complete:
                body_chunks.append(message.get("body", b""))
                if not message.get("more_body", False):
                    body_complete = True
            return message

        # Capture response status code from send
        status_code = 0

        async def logging_send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        # Log request start
        logger.info(
            f"Request started: {method} {path}",
            extra={"extra_fields": {
                "request_id": request_id,
                "method": method,
                "path": path,
                "query_params": query_params,
                "client": client_host,
                "user_agent": user_agent,
            }}
        )

        # Process request
        try:
            await self.app(scope, logging_receive, logging_send)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {method} {path} - {str(e)}",
                exc_info=True,
                extra={"extra_fields": {
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                }}
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log body at DEBUG level (after request completes, body is cached)
        if logger.isEnabledFor(logging.DEBUG) and body_chunks and method in ["POST", "PUT", "PATCH"]:
            try:
                full_body = b"".join(body_chunks)
                if full_body:
                    try:
                        body = json.loads(full_body)
                        body = filter_sensitive_data(body)
                        body_str = json.dumps(body, ensure_ascii=False)
                        body = truncate_large_data(body_str, max_length=5000)
                    except json.JSONDecodeError:
                        body = truncate_large_data(
                            full_body.decode('utf-8', errors='ignore'), max_length=1000
                        )
                    logger.debug(
                        f"Request body: {body}",
                        extra={"extra_fields": {"request_id": request_id}}
                    )
            except Exception as e:
                logger.warning(f"Failed to log request body: {e}")

        # Determine log level based on status code
        if status_code < 400:
            log_level = logging.INFO
        elif status_code < 500:
            log_level = logging.WARNING
        else:
            log_level = logging.ERROR

        # Log response
        logger.log(
            log_level,
            f"Request completed: {method} {path} - {status_code} ({duration_ms:.2f}ms)",
            extra={"extra_fields": {
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            }}
        )
