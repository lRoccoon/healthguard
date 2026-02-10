"""
Chat API endpoints - Handle conversational interactions.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
import uuid
from datetime import datetime

from ..models import ChatMessage
from ..utils.auth import get_current_user_id
from ..core import MemoryManager
from ..storage import LocalStorage
from ..config import settings
from ..agents.orchestrator import AgentOrchestrator

router = APIRouter(prefix="/chat", tags=["chat"])


# Initialize storage (should be done via dependency injection in production)
storage = LocalStorage(settings.local_storage_path)


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
    
    # Initialize orchestrator
    orchestrator = AgentOrchestrator(memory_manager)
    
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
