"""
User Model - Defines the user data structure.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user model with common fields."""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation model with password."""
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    """User update model - all fields optional."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


class User(UserBase):
    """User model with all fields."""
    user_id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    # Health profile
    has_insulin_resistance: bool = True
    health_goals: Optional[str] = None

    # Onboarding
    onboarding_completed: bool = False
    agent_persona: Optional[str] = None  # User-defined agent personality
    preferred_language: str = "zh"  # zh or en

    class Config:
        from_attributes = True


class UserInDB(User):
    """User model as stored in database with hashed password."""
    hashed_password: str


class Token(BaseModel):
    """JWT token response model."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[str] = None
    username: Optional[str] = None
