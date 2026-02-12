"""
Chat API endpoints - Handle conversational interactions.
Supports text messages and image attachments for multimodal analysis.
"""

import base64
import json
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
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


@router.post("/message")
async def send_message(
    message: ChatMessage,
    user_id: str = Depends(get_current_user_id),
    stream: bool = Query(False, description="Enable streaming output")
):
    """
    Send a chat message and get AI response.

    Args:
        message: Chat message from user
        user_id: Current user ID from token
        stream: Enable Server-Sent Events streaming

    Returns:
        ChatMessage (stream=false) or StreamingResponse (stream=true)
    """
    # Initialize memory manager for user
    memory_manager = MemoryManager(storage, user_id)

    # Initialize orchestrator with LLM provider
    llm_provider = _get_llm_provider()
    orchestrator = AgentOrchestrator(
        memory_manager, llm_provider=llm_provider, api_mode=settings.llm_api_mode
    )

    # Non-streaming mode (default, backward compatible)
    if not stream:
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

    # Streaming mode
    async def event_generator():
        accumulated_content = ""
        routing_info = None

        try:
            async for event in orchestrator.process_message_stream(
                user_message=message.content,
                user_id=user_id,
                additional_context={}
            ):
                try:
                    if event["type"] == "routing":
                        routing_info = event
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                    elif event["type"] == "content":
                        content = event["content"]
                        accumulated_content += content
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                    elif event["type"] == "done":
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                        # Save chat to log after streaming completes
                        try:
                            session_id = str(uuid.uuid4())
                            await memory_manager.save_chat_log(session_id, [
                                {
                                    "role": message.role,
                                    "content": message.content,
                                    "timestamp": message.timestamp.isoformat() if hasattr(message.timestamp, 'isoformat') else str(message.timestamp)
                                },
                                {
                                    "role": "assistant",
                                    "content": accumulated_content,
                                    "timestamp": datetime.now().isoformat(),
                                    "agent": routing_info.get("agent") if routing_info else "unknown",
                                    "routing": routing_info
                                }
                            ])
                        except Exception:
                            # Log saving failure shouldn't break the stream
                            pass

                    elif event["type"] == "error":
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                        return

                except GeneratorExit:
                    # Client disconnected
                    return
                except Exception as inner_e:
                    yield f"data: {json.dumps({'type':'error','error':str(inner_e)}, ensure_ascii=False)}\n\n"
                    return

        except GeneratorExit:
            # Client disconnected during iteration
            return
        except Exception as e:
            try:
                yield f"data: {json.dumps({'type':'error','error':str(e)}, ensure_ascii=False)}\n\n"
            except GeneratorExit:
                return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.post("/message-with-image")
async def send_message_with_image(
    content: str = Form(...),
    images: Optional[List[UploadFile]] = File(None),
    user_id: str = Depends(get_current_user_id),
    stream: bool = Form(False, description="Enable streaming output")
):
    """
    Send a chat message with optional image attachments.
    Images are analyzed using multimodal LLM (no traditional OCR).

    Args:
        content: Text message content
        images: Optional image files to attach
        user_id: Current user ID from token
        stream: Enable Server-Sent Events streaming

    Returns:
        ChatMessage (stream=false) or StreamingResponse (stream=true)
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

    # Non-streaming mode (default, backward compatible)
    if not stream:
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

    # Streaming mode
    async def event_generator():
        accumulated_content = ""
        routing_info = None

        try:
            async for event in orchestrator.process_message_stream(
                user_message=content,
                user_id=user_id,
                additional_context=additional_context
            ):
                try:
                    if event["type"] == "routing":
                        routing_info = event
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                    elif event["type"] == "content":
                        content_chunk = event["content"]
                        accumulated_content += content_chunk
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                    elif event["type"] == "done":
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                        # Save chat to log after streaming completes
                        try:
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
                                    "content": accumulated_content,
                                    "timestamp": datetime.now().isoformat(),
                                    "agent": routing_info.get("agent") if routing_info else "unknown",
                                    "routing": routing_info
                                }
                            ])
                        except Exception:
                            # Log saving failure shouldn't break the stream
                            pass

                    elif event["type"] == "error":
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                        return

                except GeneratorExit:
                    # Client disconnected
                    return
                except Exception as inner_e:
                    yield f"data: {json.dumps({'type':'error','error':str(inner_e)}, ensure_ascii=False)}\n\n"
                    return

        except GeneratorExit:
            # Client disconnected during iteration
            return
        except Exception as e:
            try:
                yield f"data: {json.dumps({'type':'error','error':str(e)}, ensure_ascii=False)}\n\n"
            except GeneratorExit:
                return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


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


@router.post("/voice")
async def send_voice_message(
    audio: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Send a voice message for transcription and processing.

    This endpoint receives an audio file, transcribes it to text,
    and then processes it through the chat agent system.

    Args:
        audio: Audio file (m4a, mp3, wav, etc.)
        user_id: Current user ID from token

    Returns:
        ChatMessage: Response with transcription and AI analysis
    """
    try:
        # Read audio file
        audio_data = await audio.read()

        # TODO: Implement speech-to-text transcription
        # Options:
        # 1. OpenAI Whisper API: https://platform.openai.com/docs/guides/speech-to-text
        # 2. Local Whisper model
        # 3. Cloud providers (Google Speech-to-Text, Azure, etc.)

        # For now, return a placeholder response
        transcribed_text = "[Voice transcription not yet implemented. Please configure a speech-to-text service.]"

        # Initialize memory manager for user
        memory_manager = MemoryManager(storage, user_id)

        # Initialize orchestrator with LLM provider
        llm_provider = _get_llm_provider()
        orchestrator = AgentOrchestrator(
            memory_manager, llm_provider=llm_provider, api_mode=settings.llm_api_mode
        )

        # Process transcribed message through agent system
        agent_response = await orchestrator.process_message(
            user_message=transcribed_text,
            user_id=user_id,
            additional_context={"audio_duration": len(audio_data)}
        )

        # Save chat to log
        session_id = str(uuid.uuid4())
        await memory_manager.save_chat_log(session_id, [
            {
                "role": "user",
                "content": transcribed_text,
                "timestamp": datetime.now().isoformat(),
                "type": "voice",
                "audio_size": len(audio_data)
            },
            {
                "role": "assistant",
                "content": agent_response["response"],
                "timestamp": datetime.now().isoformat(),
                "agent": agent_response.get("agent", "unknown"),
                "routing": agent_response.get("routing", {})
            }
        ])

        # Return response
        response = ChatMessage(
            role="assistant",
            content=agent_response["response"],
            timestamp=datetime.now()
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process voice message: {str(e)}"
        )
