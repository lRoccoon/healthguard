"""
Local Filesystem Storage Implementation.
This implementation stores all data on the server's local filesystem.
"""

import os
import json
import aiofiles
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import glob as glob_module
from .interface import StorageInterface


class LocalStorage(StorageInterface):
    """
    Local filesystem storage implementation.
    Stores all data in a base directory on the server.
    """

    def __init__(self, base_dir: str = "./data"):
        """
        Initialize local storage with a base directory.
        
        Args:
            base_dir: Base directory for all stored files
        """
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, path: str) -> Path:
        """Convert relative path to full absolute path within base directory."""
        full_path = (self.base_dir / path).resolve()
        
        # Security check: ensure path is within base_dir
        if not str(full_path).startswith(str(self.base_dir)):
            raise ValueError(f"Invalid path: {path} - path traversal detected")
        
        return full_path

    async def save(
        self,
        path: str,
        content: bytes | str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save content to local filesystem."""
        try:
            full_path = self._get_full_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            if isinstance(content, str):
                async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                    await f.write(content)
            else:
                async with aiofiles.open(full_path, 'wb') as f:
                    await f.write(content)
            
            # Save metadata if provided
            if metadata:
                metadata_path = full_path.with_suffix(full_path.suffix + '.meta')
                async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(metadata, indent=2))
            
            return True
        except Exception as e:
            print(f"Error saving file {path}: {e}")
            return False

    async def load(self, path: str) -> Optional[bytes]:
        """Load content from local filesystem."""
        try:
            full_path = self._get_full_path(path)
            if not full_path.exists():
                return None
            
            async with aiofiles.open(full_path, 'rb') as f:
                content = await f.read()
            
            return content
        except Exception as e:
            print(f"Error loading file {path}: {e}")
            return None

    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        try:
            full_path = self._get_full_path(path)
            return full_path.exists()
        except Exception:
            return False

    async def delete(self, path: str) -> bool:
        """Delete file from local filesystem."""
        try:
            full_path = self._get_full_path(path)
            if full_path.exists():
                full_path.unlink()
                
                # Also delete metadata file if exists
                metadata_path = full_path.with_suffix(full_path.suffix + '.meta')
                if metadata_path.exists():
                    metadata_path.unlink()
                
                return True
            return False
        except Exception as e:
            print(f"Error deleting file {path}: {e}")
            return False

    async def list(
        self,
        path: str,
        pattern: Optional[str] = None,
        recursive: bool = False
    ) -> List[str]:
        """List files in directory."""
        try:
            full_path = self._get_full_path(path)
            if not full_path.exists():
                return []
            
            if pattern:
                if recursive:
                    glob_pattern = str(full_path / "**" / pattern)
                    files = glob_module.glob(glob_pattern, recursive=True)
                else:
                    glob_pattern = str(full_path / pattern)
                    files = glob_module.glob(glob_pattern)
            else:
                if recursive:
                    files = [str(p) for p in full_path.rglob("*") if p.is_file()]
                else:
                    files = [str(p) for p in full_path.glob("*") if p.is_file()]
            
            # Convert to relative paths
            relative_paths = []
            for file_path in files:
                # Skip metadata files
                if file_path.endswith('.meta'):
                    continue
                rel_path = str(Path(file_path).relative_to(self.base_dir))
                relative_paths.append(rel_path)
            
            return sorted(relative_paths)
        except Exception as e:
            print(f"Error listing files in {path}: {e}")
            return []

    async def search(
        self,
        path: str,
        query: str,
        file_pattern: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for content within files."""
        try:
            results = []
            files = await self.list(path, pattern=file_pattern, recursive=True)
            
            for file_path in files:
                content = await self.load(file_path)
                if content is None:
                    continue
                
                try:
                    # Try to decode as text
                    text_content = content.decode('utf-8')
                    lines = text_content.split('\n')
                    
                    # Search for query in each line
                    for line_num, line in enumerate(lines, 1):
                        if query.lower() in line.lower():
                            results.append({
                                'file': file_path,
                                'line_number': line_num,
                                'content': line.strip(),
                                'match': query
                            })
                except UnicodeDecodeError:
                    # Skip binary files
                    continue
            
            return results
        except Exception as e:
            print(f"Error searching in {path}: {e}")
            return []

    async def get_metadata(self, path: str) -> Optional[Dict[str, Any]]:
        """Get file metadata."""
        try:
            full_path = self._get_full_path(path)
            if not full_path.exists():
                return None
            
            stat = full_path.stat()
            metadata = {
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'path': path
            }
            
            # Load custom metadata if exists
            metadata_path = full_path.with_suffix(full_path.suffix + '.meta')
            if metadata_path.exists():
                async with aiofiles.open(metadata_path, 'r', encoding='utf-8') as f:
                    custom_meta = json.loads(await f.read())
                    metadata.update(custom_meta)
            
            return metadata
        except Exception as e:
            print(f"Error getting metadata for {path}: {e}")
            return None

    async def append(self, path: str, content: str) -> bool:
        """Append content to existing file."""
        try:
            full_path = self._get_full_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(full_path, 'a', encoding='utf-8') as f:
                await f.write(content)
            
            return True
        except Exception as e:
            print(f"Error appending to file {path}: {e}")
            return False
