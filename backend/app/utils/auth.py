"""
Authentication utilities - JWT token handling and password hashing.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import settings
from ..models import TokenData

# Bearer token security
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """Hash a password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: JWT token string
        
    Returns:
        Optional[TokenData]: Token data if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        
        if user_id is None:
            return None
        
        return TokenData(user_id=user_id, username=username)
    except JWTError:
        return None


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Dependency to get current user ID from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        str: User ID
        
    Raises:
        HTTPException: If token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    token_data = decode_access_token(token)
    
    if token_data is None or token_data.user_id is None:
        raise credentials_exception
    
    return token_data.user_id


# User storage - using persistent file-based storage
from ..storage.user_storage import get_user_storage
import uuid
import asyncio


def get_user_from_db(user_id: str) -> Optional[dict]:
    """Get user from database by ID."""
    try:
        return asyncio.run(get_user_storage().get_user(user_id))
    except Exception as e:
        print(f"Error getting user {user_id}: {e}")
        return None


def get_user_by_username(username: str) -> Optional[dict]:
    """Get user from database by username."""
    try:
        return asyncio.run(get_user_storage().get_user_by_username(username))
    except Exception as e:
        print(f"Error getting user by username {username}: {e}")
        return None


def create_user_in_db(username: str, hashed_password: str, email: Optional[str] = None) -> dict:
    """Create a new user in database."""
    try:
        user_id = str(uuid.uuid4())
        return asyncio.run(get_user_storage().create_user(user_id, username, hashed_password, email))
    except Exception as e:
        print(f"Error creating user {username}: {e}")
        raise


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate a user by username and password.
    
    Args:
        username: Username
        password: Plain text password
        
    Returns:
        Optional[dict]: User data if authenticated, None otherwise
    """
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user
