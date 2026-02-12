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


def _decode_and_truncate(data: bytes, max_length: int = 5000) -> str:
    """Decode response/request bytes and truncate for safe logging."""
    return truncate_large_data(data.decode("utf-8", errors="ignore"), max_length=max_length)


def _sanitize_text_or_json(text: str) -> str:
    """Filter sensitive data if payload is JSON, fallback to plain text."""
    try:
        payload = json.loads(text)
        filtered_payload = filter_sensitive_data(payload)
        return truncate_large_data(json.dumps(filtered_payload, ensure_ascii=False), max_length=5000)
    except json.JSONDecodeError:
        return truncate_large_data(text, max_length=5000)


def _extract_error_reason(response_text: str) -> Optional[str]:
    """Extract a concise error reason from response body."""
    try:
        payload = json.loads(response_text)
        if isinstance(payload, dict):
            for key in ("detail", "message", "error", "reason"):
                value = payload.get(key)
                if value:
                    return str(value)
            return truncate_large_data(json.dumps(payload, ensure_ascii=False), max_length=500)
        if isinstance(payload, list) and payload:
            return truncate_large_data(json.dumps(payload, ensure_ascii=False), max_length=500)
    except json.JSONDecodeError:
        if response_text:
            return truncate_large_data(response_text, max_length=500)
    return None


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

        # Capture response info from send
        status_code = 0
        response_chunks = []
        response_body_complete = False
        response_headers = {}

        async def logging_send(message):
            nonlocal status_code, response_body_complete, response_headers
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                raw_headers = message.get("headers", [])
                response_headers = {
                    k.decode("utf-8", errors="ignore"): v.decode("utf-8", errors="ignore")
                    for k, v in raw_headers
                }
            elif message["type"] == "http.response.body" and not response_body_complete:
                response_chunks.append(message.get("body", b""))
                if not message.get("more_body", False):
                    response_body_complete = True
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

        request_body_text = None
        response_body_text = None

        # Parse request body (always), and print a dedicated line in DEBUG
        if body_chunks:
            try:
                full_body = b"".join(body_chunks)
                if full_body:
                    request_body_text = _sanitize_text_or_json(_decode_and_truncate(full_body, max_length=5000))
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            f"Request body: {request_body_text}",
                            extra={"extra_fields": {
                                "request_id": request_id,
                                "request_body": request_body_text,
                            }}
                        )
            except Exception as e:
                logger.warning(f"Failed to parse request body: {e}")

        # Parse response body (always), and print a dedicated line in DEBUG
        if response_chunks:
            try:
                full_response_body = b"".join(response_chunks)
                if full_response_body:
                    response_body_text = _sanitize_text_or_json(_decode_and_truncate(full_response_body, max_length=5000))
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            f"Response body: {response_body_text}",
                            extra={"extra_fields": {
                                "request_id": request_id,
                                "response_body": response_body_text,
                            }}
                        )
            except Exception as e:
                logger.warning(f"Failed to parse response body: {e}")

        error_reason = _extract_error_reason(response_body_text or "") if status_code >= 400 else None

        # Determine log level based on status code
        if status_code < 400:
            log_level = logging.INFO
        elif status_code < 500:
            log_level = logging.WARNING
        else:
            log_level = logging.ERROR

        # Log response
        completion_message = (
            f"Request completed: {method} {path} - {status_code} ({duration_ms:.2f}ms)"
            f" | request_body={request_body_text or '-'}"
            f" | response_body={response_body_text or '-'}"
        )
        if error_reason:
            completion_message += f" | error_reason={error_reason}"

        logger.log(
            log_level,
            completion_message,
            extra={"extra_fields": {
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "request_body": request_body_text,
                "response_body": response_body_text,
                "response_headers": filter_sensitive_data(response_headers),
                "error_reason": error_reason,
            }}
        )
