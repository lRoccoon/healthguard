"""Storage module - provides interface and implementations for data persistence."""

from .interface import StorageInterface
from .local_storage import LocalStorage
from .user_storage import UserStorage, init_user_storage, get_user_storage

__all__ = ['StorageInterface', 'LocalStorage', 'UserStorage', 'init_user_storage', 'get_user_storage']
