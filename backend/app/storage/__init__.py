"""Storage module - provides interface and implementations for data persistence."""

from .interface import StorageInterface
from .local_storage import LocalStorage

__all__ = ['StorageInterface', 'LocalStorage']
