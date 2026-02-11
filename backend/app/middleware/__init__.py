"""
Middleware package for HealthGuard backend.
"""

from .logging_middleware import RequestLoggingMiddleware

__all__ = ["RequestLoggingMiddleware"]
