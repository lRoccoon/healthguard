"""
Session Models - Defines structures for chat sessions.
"""

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field


class SessionMetadata(BaseModel):
    """Chat session metadata model."""
    session_id: str
    user_id: str
    title: Optional[str] = None  # Auto-generated from first message or user-defined
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_message_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_count: int = 0
    is_active: bool = True


class Session(BaseModel):
    """Full session with messages."""
    metadata: SessionMetadata
    messages: List[dict]  # List of message dicts


class SessionList(BaseModel):
    """List of session metadata."""
    sessions: List[SessionMetadata]
