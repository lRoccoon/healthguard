"""
Health API endpoints - Handle HealthKit data sync and health records.
"""

import base64
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from typing import List, Optional
from datetime import date, datetime
import uuid

from ..models import HealthKitData, FoodEntry, MedicalRecord
from ..utils.auth import get_current_user_id
from ..core import MemoryManager
from ..storage import LocalStorage
from ..config import settings
from ..agents.orchestrator import AgentOrchestrator
from ..llm.factory import create_llm_provider

router = APIRouter(prefix="/health", tags=["health"])

# Initialize storage
storage = LocalStorage(settings.local_storage_path)


def _get_llm_provider():
    """Get configured LLM provider or None."""
    api_key = settings.llm_api_key or settings.openai_api_key
    if not api_key:
        return None
    return create_llm_provider(
        provider=settings.llm_provider,
        api_key=api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
    )


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


@router.post("/food-with-image", response_model=FoodEntry, status_code=status.HTTP_201_CREATED)
async def log_food_with_image(
    description: str = Form(default=""),
    image: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Analyze food from an image and log the entry.

    Uses Diet Agent with multimodal LLM for food recognition and nutritional analysis.

    Args:
        description: Optional user description of the food
        image: Food image file
        user_id: Current user ID from token

    Returns:
        FoodEntry: Created food entry with AI analysis
    """
    # Validate image type
    allowed_types = {"image/jpeg", "image/png", "image/jpg", "image/webp", "image/gif"}
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type: {image.content_type}"
        )

    # Read image data
    image_data = await image.read()
    image_base64 = base64.b64encode(image_data).decode("utf-8")

    # Initialize memory manager and orchestrator
    memory_manager = MemoryManager(storage, user_id)
    llm_provider = _get_llm_provider()
    orchestrator = AgentOrchestrator(
        memory_manager, llm_provider=llm_provider, api_mode=settings.llm_api_mode
    )

    # Prepare user message
    user_message = description if description else "请分析这张食物图片，告诉我食物名称、热量、GI值，以及对胰岛素抵抗的影响。"

    # Process with Diet Agent
    agent_response = await orchestrator.process_message(
        user_message=user_message,
        user_id=user_id,
        additional_context={
            "image_base64_list": [{
                "data": image_base64,
                "media_type": image.content_type
            }],
            "force_agent": "diet"  # Force routing to Diet Agent
        }
    )

    # Extract analysis from response
    analysis_text = agent_response.get("response", "")

    # Try to extract structured information from analysis
    # (This is a simple extraction; could be improved with structured output)
    food_name = "食物图片"
    gi_value = None
    calories = None
    ir_assessment = None

    # Parse response for structured data
    if "卡路里" in analysis_text or "热量" in analysis_text or "kcal" in analysis_text.lower():
        # Try to extract calories (simple pattern matching)
        import re
        cal_match = re.search(r'(\d+\.?\d*)\s*(大?卡|kcal|千卡)', analysis_text, re.IGNORECASE)
        if cal_match:
            calories = float(cal_match.group(1))

    if "低GI" in analysis_text or "Low GI" in analysis_text:
        gi_value = "Low"
    elif "中GI" in analysis_text or "Medium GI" in analysis_text:
        gi_value = "Medium"
    elif "高GI" in analysis_text or "High GI" in analysis_text:
        gi_value = "High"

    # Create food entry
    food_entry = FoodEntry(
        name=food_name,
        description=description,
        calories=calories,
        gi_value=gi_value,
        analysis=analysis_text,
        ir_assessment=f"Based on image analysis"
    )

    # Append to daily log
    today = date.today()
    await memory_manager.append_to_daily_log(
        target_date=today,
        section="Diet",
        content=f"**{food_name}** (图片分析)\n{description if description else ''}\n{analysis_text[:200]}..."
    )

    return food_entry


@router.post("/medical-record", response_model=MedicalRecord, status_code=status.HTTP_201_CREATED)
async def upload_medical_record(
    file: UploadFile = File(...),
    description: str = Form(default=""),
    user_id: str = Depends(get_current_user_id)
):
    """
    Upload and analyze a medical record (image or PDF).

    Uses Medical Agent with multimodal LLM or OCR for extracting health indicators.

    Args:
        file: Uploaded medical record file
        description: Optional description of the medical record
        user_id: Current user ID from token

    Returns:
        MedicalRecord: Created medical record with OCR analysis
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

    # Read file content
    content = await file.read()

    # Save file
    await memory_manager.save_medical_record(
        filename=filename,
        content=content,
        metadata={
            "original_filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "description": description
        }
    )

    # Perform OCR/analysis if it's an image
    extracted_data = None
    analysis = None

    if "image" in file.content_type:
        # Initialize orchestrator with LLM provider
        llm_provider = _get_llm_provider()

        if llm_provider:
            orchestrator = AgentOrchestrator(
                memory_manager, llm_provider=llm_provider, api_mode=settings.llm_api_mode
            )

            # Convert image to base64
            image_base64 = base64.b64encode(content).decode("utf-8")

            # Prepare message for Medical Agent
            user_message = description if description else "请分析这份医疗报告，提取关键健康指标（如血糖、胰岛素、HbA1c等），并评估是否存在胰岛素抵抗风险。"

            try:
                # Process with Medical Agent
                agent_response = await orchestrator.process_message(
                    user_message=user_message,
                    user_id=user_id,
                    additional_context={
                        "image_base64_list": [{
                            "data": image_base64,
                            "media_type": file.content_type
                        }],
                        "force_agent": "medical"  # Force routing to Medical Agent
                    }
                )

                analysis = agent_response.get("response", "")

                # Extract structured data (simple pattern matching)
                # Could be improved with structured output from LLM
                extracted_data = {
                    "analyzed": True,
                    "agent_type": "multimodal_llm"
                }

                # Try to extract key indicators
                import re
                indicators = {}

                # Blood glucose patterns
                glucose_match = re.search(r'血糖.*?(\d+\.?\d*)\s*(mmol/L|mg/dL)', analysis)
                if glucose_match:
                    indicators["blood_glucose"] = {
                        "value": float(glucose_match.group(1)),
                        "unit": glucose_match.group(2)
                    }

                # HbA1c patterns
                hba1c_match = re.search(r'HbA1c.*?(\d+\.?\d*)\s*%', analysis)
                if hba1c_match:
                    indicators["hba1c"] = {
                        "value": float(hba1c_match.group(1)),
                        "unit": "%"
                    }

                # Insulin patterns
                insulin_match = re.search(r'胰岛素.*?(\d+\.?\d*)\s*(mIU/L|μIU/mL)', analysis)
                if insulin_match:
                    indicators["insulin"] = {
                        "value": float(insulin_match.group(1)),
                        "unit": insulin_match.group(2)
                    }

                if indicators:
                    extracted_data["indicators"] = indicators

            except Exception as e:
                analysis = f"OCR分析失败: {str(e)}"
                print(f"Medical record analysis error: {e}")
        else:
            analysis = "需要配置 LLM API 密钥才能进行医疗记录分析"
    else:
        # PDF files - placeholder for future PDF parsing
        analysis = "PDF 文件分析功能将在未来版本中实现"

    record = MedicalRecord(
        record_id=record_id,
        user_id=user_id,
        filename=filename,
        file_type="image" if "image" in file.content_type else "pdf",
        upload_date=datetime.now(),
        extracted_data=extracted_data,
        analysis=analysis
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
