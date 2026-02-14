"""
Authentication API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta

from ..models import UserCreate, Token, User
from ..utils.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    create_user_in_db,
    get_user_by_username,
    get_current_user_id,
    get_user_from_db
)
from ..config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Register a new user.

    Args:
        user_data: User registration data

    Returns:
        User: Created user object

    Raises:
        HTTPException: If username already exists
    """
    # Check if username already exists
    existing_user = await get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Hash password and create user
    hashed_password = get_password_hash(user_data.password)
    user = await create_user_in_db(
        username=user_data.username,
        hashed_password=hashed_password,
        email=user_data.email
    )

    # Remove sensitive data before returning
    user_response = User(**{k: v for k, v in user.items() if k != 'hashed_password'})

    return user_response


@router.post("/login", response_model=Token)
async def login(username: str, password: str):
    """
    Login and get access token.

    Args:
        username: Username
        password: Password

    Returns:
        Token: JWT access token

    Raises:
        HTTPException: If authentication fails
    """
    user = await authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["user_id"], "username": user["username"]},
        expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=User)
async def get_current_user(user_id: str = Depends(get_current_user_id)):
    """
    Get current user information.

    Args:
        user_id: Current user ID from token

    Returns:
        User: Current user object

    Raises:
        HTTPException: If user not found
    """
    user = await get_user_from_db(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user_response = User(**{k: v for k, v in user.items() if k != 'hashed_password'})
    return user_response
