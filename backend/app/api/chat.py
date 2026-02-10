"""
Chat API endpoints - Handle conversational interactions.
Supports text messages and image attachments for multimodal analysis.
"""

import base64
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from typing import List, Optional
import uuid
from datetime import datetime

from ..models import ChatMessage
from ..utils.auth import get_current_user_id
from ..core import MemoryManager
from ..storage import LocalStorage
from ..config import settings
from ..agents.orchestrator import AgentOrchestrator
from ..llm.factory import create_llm_provider

router = APIRouter(prefix="/chat", tags=["chat"])


# Initialize storage (should be done via dependency injection in production)
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


@router.post("/message", response_model=ChatMessage)
async def send_message(
    message: ChatMessage,
    user_id: str = Depends(get_current_user_id)
):
    """
    Send a chat message and get AI response.
    
    Args:
        message: Chat message from user
        user_id: Current user ID from token
        
    Returns:
        ChatMessage: AI assistant response
    """
    # Initialize memory manager for user
    memory_manager = MemoryManager(storage, user_id)
    
    # Initialize orchestrator with LLM provider
    llm_provider = _get_llm_provider()
    orchestrator = AgentOrchestrator(
        memory_manager, llm_provider=llm_provider, api_mode=settings.llm_api_mode
    )
    
    # Process message through agent system
    agent_response = await orchestrator.process_message(
        user_message=message.content,
        user_id=user_id,
        additional_context={}
    )
    
    # Save chat to log
    session_id = str(uuid.uuid4())
    await memory_manager.save_chat_log(session_id, [
        {
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp.isoformat() if hasattr(message.timestamp, 'isoformat') else str(message.timestamp)
        },
        {
            "role": "assistant",
            "content": agent_response["response"],
            "timestamp": datetime.now().isoformat(),
            "agent": agent_response.get("agent", "unknown"),
            "routing": agent_response.get("routing", {})
        }
    ])
    
    response = ChatMessage(
        role="assistant",
        content=agent_response["response"],
        timestamp=datetime.now()
    )
    
    return response


@router.post("/message-with-image", response_model=ChatMessage)
async def send_message_with_image(
    content: str = Form(...),
    images: Optional[List[UploadFile]] = File(None),
    user_id: str = Depends(get_current_user_id)
):
    """
    Send a chat message with optional image attachments.
    Images are analyzed using multimodal LLM (no traditional OCR).
    
    Args:
        content: Text message content
        images: Optional image files to attach
        user_id: Current user ID from token
        
    Returns:
        ChatMessage: AI assistant response
    """
    # Initialize memory manager for user
    memory_manager = MemoryManager(storage, user_id)
    
    # Initialize orchestrator with LLM provider
    llm_provider = _get_llm_provider()
    orchestrator = AgentOrchestrator(
        memory_manager, llm_provider=llm_provider, api_mode=settings.llm_api_mode
    )
    
    # Process images if provided
    additional_context = {}
    if images:
        image_base64_list = []
        allowed_types = {"image/jpeg", "image/png", "image/jpg", "image/webp", "image/gif"}
        for img_file in images:
            if img_file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported image type: {img_file.content_type}"
                )
            img_data = await img_file.read()
            image_base64_list.append({
                "data": base64.b64encode(img_data).decode("utf-8"),
                "media_type": img_file.content_type,
            })
        additional_context["image_base64_list"] = image_base64_list
    
    # Process message through agent system
    agent_response = await orchestrator.process_message(
        user_message=content,
        user_id=user_id,
        additional_context=additional_context
    )
    
    # Save chat to log
    session_id = str(uuid.uuid4())
    await memory_manager.save_chat_log(session_id, [
        {
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "has_images": bool(images),
        },
        {
            "role": "assistant",
            "content": agent_response["response"],
            "timestamp": datetime.now().isoformat(),
            "agent": agent_response.get("agent", "unknown"),
            "routing": agent_response.get("routing", {})
        }
    ])
    
    response = ChatMessage(
        role="assistant",
        content=agent_response["response"],
        timestamp=datetime.now()
    )
    
    return response


@router.get("/history", response_model=List[dict])
async def get_chat_history(
    days: int = 7,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get chat history for the user.
    
    Args:
        days: Number of days to look back
        user_id: Current user ID from token
        
    Returns:
        List of chat sessions
    """
    memory_manager = MemoryManager(storage, user_id)
    
    # List chat log files
    chat_path = f"users/{user_id}/raw_chats"
    files = await storage.list(chat_path, pattern="*.json")
    
    history = []
    for file_path in files[-10:]:  # Get last 10 sessions
        content = await storage.load(file_path)
        if content:
            import json
            messages = json.loads(content.decode('utf-8'))
            history.append({
                "session_id": file_path.split('/')[-1].replace('.json', ''),
                "messages": messages
            })
    
    return history
