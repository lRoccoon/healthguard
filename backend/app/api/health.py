"""
Health API endpoints - Handle HealthKit data sync and health records.
"""

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from typing import List
from datetime import date, datetime
import uuid

from ..models import HealthKitData, FoodEntry, MedicalRecord
from ..utils.auth import get_current_user_id
from ..core import MemoryManager
from ..storage import LocalStorage
from ..config import settings

router = APIRouter(prefix="/health", tags=["health"])

# Initialize storage
storage = LocalStorage(settings.local_storage_path)


@router.post("/sync-health", status_code=status.HTTP_201_CREATED)
async def sync_health_data(
    health_data: HealthKitData,
    user_id: str = Depends(get_current_user_id)
):
    """
    Sync HealthKit data from iOS app.
    
    Args:
        health_data: HealthKit data from iOS
        user_id: Current user ID from token
        
    Returns:
        Success message
    """
    # Override user_id from token
    health_data.user_id = user_id
    
    memory_manager = MemoryManager(storage, user_id)
    
    # Update daily log with fitness data
    fitness_data = {
        "steps": health_data.steps,
        "active_energy": health_data.active_energy,
        "exercise_minutes": health_data.exercise_minutes,
        "heart_rate": health_data.heart_rate_avg,
        "analysis": "Fitness data synced from HealthKit. Analysis pending."
    }
    
    await memory_manager.append_to_daily_log(
        target_date=health_data.date,
        section="Fitness Update",
        content=f"**Steps**: {health_data.steps}\n**Active Energy**: {health_data.active_energy} kcal\n**Heart Rate**: {health_data.heart_rate_avg} bpm"
    )
    
    return {
        "status": "success",
        "message": "Health data synced successfully",
        "date": health_data.date.isoformat()
    }


@router.post("/food", response_model=FoodEntry, status_code=status.HTTP_201_CREATED)
async def log_food(
    food: FoodEntry,
    user_id: str = Depends(get_current_user_id)
):
    """
    Log a food entry.
    
    Args:
        food: Food entry data
        user_id: Current user ID from token
        
    Returns:
        FoodEntry: Created food entry with analysis
    """
    memory_manager = MemoryManager(storage, user_id)
    
    # TODO: Call Diet Agent for analysis in Phase 3
    food.analysis = "食物分析将在 Phase 3 的 Diet Agent 中实现"
    food.ir_assessment = "等待分析"
    
    # Append to daily log
    today = date.today()
    await memory_manager.append_to_daily_log(
        target_date=today,
        section="Diet",
        content=f"**{food.name}**: {food.description or 'No description'}"
    )
    
    return food


@router.post("/medical-record", response_model=MedicalRecord, status_code=status.HTTP_201_CREATED)
async def upload_medical_record(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Upload a medical record (image or PDF).
    
    Args:
        file: Uploaded file
        user_id: Current user ID from token
        
    Returns:
        MedicalRecord: Created medical record with metadata
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not supported"
        )
    
    memory_manager = MemoryManager(storage, user_id)
    
    # Generate record ID
    record_id = str(uuid.uuid4())
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'dat'
    filename = f"{record_id}.{file_extension}"
    
    # Read and save file
    content = await file.read()
    await memory_manager.save_medical_record(
        filename=filename,
        content=content,
        metadata={
            "original_filename": file.filename,
            "content_type": file.content_type,
            "size": len(content)
        }
    )
    
    # TODO: Call Medical Agent for OCR and analysis in Phase 3
    
    record = MedicalRecord(
        record_id=record_id,
        user_id=user_id,
        filename=filename,
        file_type="image" if "image" in file.content_type else "pdf",
        upload_date=datetime.now(),
        extracted_data=None,
        analysis="OCR 和分析将在 Phase 3 的 Medical Agent 中实现"
    )
    
    return record


@router.get("/records", response_model=List[dict])
async def list_medical_records(user_id: str = Depends(get_current_user_id)):
    """
    List all medical records for the user.
    
    Args:
        user_id: Current user ID from token
        
    Returns:
        List of medical record metadata
    """
    memory_manager = MemoryManager(storage, user_id)
    records = await memory_manager.list_medical_records()
    return records


@router.get("/daily-logs")
async def get_daily_logs(
    days: int = 7,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get recent daily logs.
    
    Args:
        days: Number of days to retrieve
        user_id: Current user ID from token
        
    Returns:
        List of daily logs
    """
    memory_manager = MemoryManager(storage, user_id)
    logs = await memory_manager.get_recent_logs(days)
    return logs
