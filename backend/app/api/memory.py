"""
Memory API endpoints - Manage persistent memories and consolidation.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional
from datetime import date, datetime, timedelta

from ..utils.auth import get_current_user_id
from ..core import MemoryManager
from ..core.memory_consolidator import MemoryConsolidator
from ..storage import LocalStorage
from ..config import settings
from ..llm.factory import create_llm_provider

router = APIRouter(prefix="/memory", tags=["memory"])

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


@router.get("/main")
async def get_main_memory(
    user_id: str = Depends(get_current_user_id)
):
    """
    Get the main MEMORY.md file content.

    Args:
        user_id: Current user ID from token

    Returns:
        Memory content
    """
    memory_manager = MemoryManager(storage, user_id)
    consolidator = MemoryConsolidator(storage, user_id)

    # Get main memory path
    memory_path = consolidator._get_memory_path()

    if not await storage.exists(memory_path):
        return {"content": None, "message": "No memory file found"}

    content = await storage.load(memory_path)
    if content:
        return {"content": content.decode('utf-8')}

    return {"content": None}


@router.get("/daily/{target_date}")
async def get_daily_memory(
    target_date: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get daily memory for a specific date.

    Args:
        target_date: Date in YYYY-MM-DD format
        user_id: Current user ID from token

    Returns:
        Daily memory content
    """
    try:
        date_obj = date.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    consolidator = MemoryConsolidator(storage, user_id)

    # Get daily memory path
    daily_path = consolidator._get_daily_memory_path(date_obj)

    if not await storage.exists(daily_path):
        return {"content": None, "message": f"No memory found for {target_date}"}

    content = await storage.load(daily_path)
    if content:
        return {"content": content.decode('utf-8'), "date": target_date}

    return {"content": None}


@router.get("/recent")
async def get_recent_memories(
    days: int = 7,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get recent memories (main + last N days).

    Args:
        days: Number of days to look back
        user_id: Current user ID from token

    Returns:
        Combined memory content
    """
    llm_provider = _get_llm_provider()
    consolidator = MemoryConsolidator(storage, user_id, llm_provider)

    content = await consolidator.load_recent_memories(days=days)

    return {
        "content": content,
        "days": days
    }


@router.post("/consolidate/daily/{target_date}")
async def consolidate_daily_memory(
    target_date: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Manually trigger daily memory consolidation for a specific date.

    Args:
        target_date: Date in YYYY-MM-DD format
        user_id: Current user ID from token

    Returns:
        Consolidation result
    """
    try:
        date_obj = date.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    llm_provider = _get_llm_provider()
    consolidator = MemoryConsolidator(storage, user_id, llm_provider)

    success = await consolidator.consolidate_daily_memory(date_obj)

    if success:
        return {
            "success": True,
            "message": f"Daily memory consolidated for {target_date}",
            "date": target_date
        }
    else:
        return {
            "success": False,
            "message": f"No sessions found for {target_date}",
            "date": target_date
        }


@router.post("/consolidate/auto")
async def auto_consolidate_memories(
    user_id: str = Depends(get_current_user_id)
):
    """
    Automatically consolidate memories for recent days (last 7 days).
    This should be called periodically (e.g., daily via cron job).

    Args:
        user_id: Current user ID from token

    Returns:
        Consolidation results
    """
    llm_provider = _get_llm_provider()
    consolidator = MemoryConsolidator(storage, user_id, llm_provider)

    results = []
    today = date.today()

    # Consolidate last 7 days
    for i in range(7):
        target_date = today - timedelta(days=i)
        success = await consolidator.consolidate_daily_memory(target_date)
        results.append({
            "date": target_date.isoformat(),
            "consolidated": success
        })

    return {
        "success": True,
        "message": "Auto-consolidation completed",
        "results": results
    }
