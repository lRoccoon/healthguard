"""
Storage Interface - Abstract base class for all storage implementations.
This interface enables seamless switching between Local, S3, OSS, etc.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime


class StorageInterface(ABC):
    """
    Abstract storage interface that defines the contract for all storage implementations.
    Future implementations can include S3Storage, OSSStorage, etc.
    """

    @abstractmethod
    async def save(
        self,
        path: str,
        content: bytes | str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save content to the specified path.
        
        Args:
            path: Relative path where content should be saved (e.g., "users/123/memories/2023-10-27.md")
            content: Content to save (can be bytes for binary files or str for text)
            metadata: Optional metadata to associate with the file
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        pass

    @abstractmethod
    async def load(self, path: str) -> Optional[bytes]:
        """
        Load content from the specified path.
        
        Args:
            path: Relative path to load from
            
        Returns:
            Optional[bytes]: File content as bytes, or None if file doesn't exist
        """
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check if a file exists at the specified path.
        
        Args:
            path: Relative path to check
            
        Returns:
            bool: True if file exists, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """
        Delete file at the specified path.
        
        Args:
            path: Relative path to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        pass

    @abstractmethod
    async def list(
        self,
        path: str,
        pattern: Optional[str] = None,
        recursive: bool = False
    ) -> List[str]:
        """
        List files in the specified directory.
        
        Args:
            path: Directory path to list
            pattern: Optional glob pattern to filter files (e.g., "*.md")
            recursive: Whether to list files recursively
            
        Returns:
            List[str]: List of file paths
        """
        pass

    @abstractmethod
    async def search(
        self,
        path: str,
        query: str,
        file_pattern: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for content within files.
        
        Args:
            path: Directory path to search in
            query: Search query string
            file_pattern: Optional pattern to filter files to search in
            
        Returns:
            List[Dict]: List of search results with file path, matched content, and line numbers
        """
        pass

    @abstractmethod
    async def get_metadata(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a file.
        
        Args:
            path: File path
            
        Returns:
            Optional[Dict]: Metadata including size, created_at, modified_at, etc.
        """
        pass

    @abstractmethod
    async def append(self, path: str, content: str) -> bool:
        """
        Append content to an existing file.
        
        Args:
            path: File path
            content: Content to append
            
        Returns:
            bool: True if append was successful
        """
        pass
