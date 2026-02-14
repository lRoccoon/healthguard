"""
User Storage - Persistent storage for user data using StorageInterface.
Replaces in-memory _users_db with file-based storage.
"""

import json
from typing import Optional, Dict
from datetime import datetime, timezone
from .local_storage import LocalStorage


class UserStorage:
    """
    Manages persistent storage of user data.
    Uses JSON files for each user stored in data/users/ directory.
    """

    def __init__(self, storage: LocalStorage):
        """
        Initialize user storage.

        Args:
            storage: StorageInterface implementation (typically LocalStorage)
        """
        self.storage = storage
        self.users_dir = "users"
        self._username_index_path = f"{self.users_dir}/username_index.json"

    async def _load_username_index(self) -> Dict[str, str]:
        """Load username to user_id index mapping."""
        content = await self.storage.load(self._username_index_path)
        if content is None:
            return {}
        try:
            return json.loads(content.decode('utf-8'))
        except Exception:
            return {}

    async def _save_username_index(self, index: Dict[str, str]) -> bool:
        """Save username to user_id index mapping."""
        try:
            content = json.dumps(index, indent=2)
            return await self.storage.save(self._username_index_path, content)
        except Exception:
            return False

    async def get_user(self, user_id: str) -> Optional[Dict]:
        """
        Get user by user_id.

        Args:
            user_id: User ID

        Returns:
            Optional[Dict]: User data or None if not found
        """
        user_path = f"{self.users_dir}/{user_id}.json"
        content = await self.storage.load(user_path)

        if content is None:
            return None

        try:
            user_data = json.loads(content.decode('utf-8'))
            # Convert datetime strings back to datetime objects
            if 'created_at' in user_data:
                user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
            if 'updated_at' in user_data:
                user_data['updated_at'] = datetime.fromisoformat(user_data['updated_at'])
            return user_data
        except Exception as e:
            print(f"Error loading user {user_id}: {e}")
            return None

    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            Optional[Dict]: User data or None if not found
        """
        # Load username index
        index = await self._load_username_index()
        user_id = index.get(username)

        if user_id is None:
            return None

        return await self.get_user(user_id)

    async def create_user(
        self,
        user_id: str,
        username: str,
        hashed_password: str,
        email: Optional[str] = None
    ) -> Dict:
        """
        Create a new user.

        Args:
            user_id: User ID (UUID)
            username: Username
            hashed_password: Hashed password
            email: Optional email

        Returns:
            Dict: Created user data
        """
        now = datetime.now(timezone.utc)

        user_data = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "is_active": True,
            "has_insulin_resistance": True,
            "health_goals": None,
            "full_name": None,
            "onboarding_completed": False,
            "agent_persona": None,
            "preferred_language": "zh"
        }

        # Save user file
        user_path = f"{self.users_dir}/{user_id}.json"
        content = json.dumps(user_data, indent=2, ensure_ascii=False)
        await self.storage.save(user_path, content)

        # Update username index
        index = await self._load_username_index()
        index[username] = user_id
        await self._save_username_index(index)

        # Convert datetime strings back to datetime objects for return
        user_data['created_at'] = now
        user_data['updated_at'] = now

        return user_data

    async def update_user(self, user_id: str, updates: Dict) -> Optional[Dict]:
        """
        Update user data.

        Args:
            user_id: User ID
            updates: Dictionary of fields to update

        Returns:
            Optional[Dict]: Updated user data or None if user not found
        """
        user = await self.get_user(user_id)
        if user is None:
            return None

        # Update fields
        user.update(updates)
        user['updated_at'] = datetime.now(timezone.utc)

        # Convert datetime objects to strings for JSON serialization
        user_data_json = user.copy()
        if isinstance(user_data_json.get('created_at'), datetime):
            user_data_json['created_at'] = user_data_json['created_at'].isoformat()
        if isinstance(user_data_json.get('updated_at'), datetime):
            user_data_json['updated_at'] = user_data_json['updated_at'].isoformat()

        # Save user file
        user_path = f"{self.users_dir}/{user_id}.json"
        content = json.dumps(user_data_json, indent=2, ensure_ascii=False)
        await self.storage.save(user_path, content)

        return user

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.

        Args:
            user_id: User ID

        Returns:
            bool: True if deleted successfully
        """
        user = await self.get_user(user_id)
        if user is None:
            return False

        # Remove from username index
        index = await self._load_username_index()
        username = user.get('username')
        if username and username in index:
            del index[username]
            await self._save_username_index(index)

        # Delete user file
        user_path = f"{self.users_dir}/{user_id}.json"
        return await self.storage.delete(user_path)

    async def list_users(self) -> list[Dict]:
        """
        List all users.

        Returns:
            list[Dict]: List of all users
        """
        files = await self.storage.list(self.users_dir, pattern="*.json", recursive=False)
        users = []

        for file_path in files:
            # Skip the username index file
            if file_path.endswith('username_index.json'):
                continue

            content = await self.storage.load(file_path)
            if content:
                try:
                    user_data = json.loads(content.decode('utf-8'))
                    # Convert datetime strings back to datetime objects
                    if 'created_at' in user_data:
                        user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
                    if 'updated_at' in user_data:
                        user_data['updated_at'] = datetime.fromisoformat(user_data['updated_at'])
                    users.append(user_data)
                except Exception:
                    continue

        return users


# Global user storage instance
_user_storage: Optional[UserStorage] = None


def init_user_storage(storage: LocalStorage = None):
    """
    Initialize the global user storage instance.

    Args:
        storage: Optional StorageInterface implementation. If None, creates LocalStorage.
    """
    global _user_storage
    if storage is None:
        storage = LocalStorage()
    _user_storage = UserStorage(storage)


def get_user_storage() -> UserStorage:
    """
    Get the global user storage instance.

    Returns:
        UserStorage: Global user storage instance

    Raises:
        RuntimeError: If user storage has not been initialized
    """
    if _user_storage is None:
        raise RuntimeError("User storage not initialized. Call init_user_storage() first.")
    return _user_storage
