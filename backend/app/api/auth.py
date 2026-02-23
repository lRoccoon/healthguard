"""
Authentication API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Form
from datetime import timedelta, datetime
from typing import Optional

from ..models import UserCreate, Token, User, UserUpdate
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
from ..storage import LocalStorage

router = APIRouter(prefix="/auth", tags=["authentication"])

# Initialize storage
storage = LocalStorage(settings.local_storage_path)


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

    # Create welcome session with initialization message
    from ..core import MemoryManager
    from uuid import uuid4

    session_id = str(uuid4())
    memory_manager = MemoryManager(storage, user["user_id"])

    # Create welcome message
    welcome_content = """👋 你好！欢迎来到 HealthGuard AI！

我是你的健康助理，专门帮助你管理胰岛素抵抗。让我先了解一下你：

1. 你希望我以什么样的方式与你交流？（比如：专业医生、温暖的朋友、严格的教练等）
2. 你的主要健康目标是什么？
3. 你更喜欢使用中文还是英文？

请随时告诉我你的需求，我会根据你的偏好调整我的回应方式！"""

    welcome_messages = [
        {
            "role": "assistant",
            "content": welcome_content,
            "timestamp": datetime.now().isoformat(),
            "agent": "system",
            "is_welcome": True
        }
    ]

    session_metadata = {
        'session_id': session_id,
        'user_id': user["user_id"],
        'created_at': datetime.now().isoformat(),
        'title': "欢迎初始化",
        'is_onboarding': True
    }

    await memory_manager.save_chat_log(session_id, welcome_messages, session_metadata)

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


@router.post("/onboarding")
async def complete_onboarding(
    agent_persona: str = Form(..., description="User-defined agent personality"),
    health_goals: Optional[str] = Form(None, description="User's health goals"),
    preferred_language: str = Form("zh", description="Preferred language (zh or en)"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Complete user onboarding by setting agent persona and preferences.

    Args:
        agent_persona: User-defined agent personality description
        health_goals: Optional health goals
        preferred_language: Preferred language (zh or en)
        user_id: Current user ID from token

    Returns:
        Updated user object
    """
    user = await get_user_from_db(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update user data
    user["onboarding_completed"] = True
    user["agent_persona"] = agent_persona
    user["preferred_language"] = preferred_language
    if health_goals:
        user["health_goals"] = health_goals
    user["updated_at"] = datetime.now()

    # Save to storage
    user_path = f"users/{user_id}/profile.json"
    import json
    user_json = json.dumps(user, default=str, ensure_ascii=False, indent=2)
    await storage.save(user_path, user_json)

    user_response = User(**{k: v for k, v in user.items() if k != 'hashed_password'})
    return user_response


@router.put("/profile")
async def update_profile(
    profile_update: UserUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update user profile information.

    Args:
        profile_update: Updated profile fields
        user_id: Current user ID from token

    Returns:
        Updated user object
    """
    user = await get_user_from_db(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update fields if provided
    if profile_update.email is not None:
        user["email"] = profile_update.email
    if profile_update.full_name is not None:
        user["full_name"] = profile_update.full_name
    if profile_update.password is not None:
        user["hashed_password"] = get_password_hash(profile_update.password)

    user["updated_at"] = datetime.now()

    # Save to storage
    user_path = f"users/{user_id}/profile.json"
    import json
    user_json = json.dumps(user, default=str, ensure_ascii=False, indent=2)
    await storage.save(user_path, user_json)

    user_response = User(**{k: v for k, v in user.items() if k != 'hashed_password'})
    return user_response
