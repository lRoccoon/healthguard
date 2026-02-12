"""
Health Data Models - Defines structures for HealthKit data and other health metrics.
"""

from datetime import datetime, date, timezone
from typing import Optional, List
from pydantic import BaseModel, Field


class HealthKitData(BaseModel):
    """HealthKit data model for iOS sync."""
    user_id: str
    date: date
    
    # Activity metrics
    steps: Optional[int] = None
    active_energy: Optional[float] = None  # kcal
    exercise_minutes: Optional[int] = None
    
    # Heart rate data
    heart_rate_avg: Optional[float] = None  # bpm
    heart_rate_min: Optional[float] = None
    heart_rate_max: Optional[float] = None
    
    # Additional metrics
    distance_walking: Optional[float] = None  # km
    flights_climbed: Optional[int] = None
    
    # Metadata
    synced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FoodEntry(BaseModel):
    """Food/meal entry model."""
    name: str
    description: Optional[str] = None
    calories: Optional[float] = None
    gi_value: Optional[str] = None  # Low, Medium, High
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    image_url: Optional[str] = None
    
    # Analysis results
    analysis: Optional[str] = None
    ir_assessment: Optional[str] = None


class MedicalRecord(BaseModel):
    """Medical record model."""
    record_id: str
    user_id: str
    filename: str
    file_type: str  # image, pdf
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # OCR and analysis results
    extracted_data: Optional[dict] = None
    analysis: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Optional attachments
    attachments: Optional[List[dict]] = None
