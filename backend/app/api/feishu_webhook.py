"""
Feishu Webhook API - Handles incoming events from Feishu bot.
Supports text messages, image uploads, and voice messages.
"""

import base64
import logging
from fastapi import APIRouter, Request, HTTPException

from ..channels.feishu import FeishuBot
from ..core import MemoryManager
from ..storage import LocalStorage
from ..config import settings
from ..agents.orchestrator import AgentOrchestrator
from ..llm.factory import create_llm_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feishu", tags=["feishu"])


def _get_feishu_bot():
    """Get configured Feishu bot or None."""
    if not settings.feishu_app_id or not settings.feishu_app_secret:
        return None
    return FeishuBot(
        app_id=settings.feishu_app_id,
        app_secret=settings.feishu_app_secret,
        verification_token=settings.feishu_verification_token,
        encrypt_key=settings.feishu_encrypt_key,
    )


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


# Track processed event IDs to avoid duplicate processing
_processed_events: set = set()
_MAX_PROCESSED_EVENTS = 1000


@router.post("/webhook")
async def feishu_webhook(request: Request):
    """
    Handle incoming Feishu webhook events.
    Supports text messages, image uploads, and voice messages.
    """
    body = await request.json()
    bot = _get_feishu_bot()

    if bot is None:
        raise HTTPException(status_code=503, detail="Feishu bot not configured")

    # Parse the event
    event = bot.parse_event(body)

    # Handle URL verification
    if event["type"] == "url_verification":
        return {"challenge": event["challenge"]}

    # Deduplicate events
    header = body.get("header", {})
    event_id = header.get("event_id", "")
    if event_id:
        if event_id in _processed_events:
            return {"code": 0, "msg": "ok"}
        _processed_events.add(event_id)
        # Prevent unbounded growth
        if len(_processed_events) > _MAX_PROCESSED_EVENTS:
            excess = len(_processed_events) - _MAX_PROCESSED_EVENTS // 2
            for _ in range(excess):
                _processed_events.pop()

    if event["type"] != "message":
        return {"code": 0, "msg": "ok"}

    # Process message based on type
    chat_id = event.get("chat_id", "")
    sender_id = event.get("sender_id", "")
    msg_type = event.get("message_type", "text")

    # Use sender's open_id as user_id for Feishu users
    user_id = f"feishu_{sender_id}" if sender_id else "feishu_anonymous"

    storage = LocalStorage(settings.local_storage_path)
    memory_manager = MemoryManager(storage, user_id)
    llm_provider = _get_llm_provider()
    orchestrator = AgentOrchestrator(
        memory_manager, llm_provider=llm_provider, api_mode=settings.llm_api_mode
    )

    additional_context = {}

    try:
        if msg_type == "text":
            user_message = event.get("text", "")

        elif msg_type == "image":
            # Download image and pass to multimodal LLM
            image_key = event.get("image_key", "")
            message_id = event.get("message_id", "")
            if image_key and message_id:
                img_bytes = await bot.download_image(message_id, image_key)
                additional_context["image_base64_list"] = [{
                    "data": base64.b64encode(img_bytes).decode("utf-8"),
                    "media_type": "image/png",
                }]
            user_message = "请分析这张图片"

        elif msg_type == "audio":
            # Download audio and convert to text
            file_key = event.get("file_key", "")
            message_id = event.get("message_id", "")
            if file_key and message_id:
                audio_bytes = await bot.download_audio(message_id, file_key)
                user_message = await bot.speech_to_text(audio_bytes)
                if not user_message:
                    user_message = "（语音识别失败，请重试或发送文字消息）"
            else:
                user_message = "（无法获取语音内容）"

        else:
            user_message = f"（暂不支持 {msg_type} 类型的消息）"

        # Process through agent system
        agent_response = await orchestrator.process_message(
            user_message=user_message,
            user_id=user_id,
            additional_context=additional_context,
        )

        # Send reply back to Feishu
        reply_text = agent_response.get("response", "抱歉，处理消息时出现错误。")
        await bot.send_text_message(chat_id, reply_text)

    except Exception as e:
        logger.exception("Error processing Feishu message")
        try:
            await bot.send_text_message(chat_id, f"抱歉，处理消息时出现错误：{e}")
        except Exception:
            logger.exception("Failed to send error message to Feishu")

    return {"code": 0, "msg": "ok"}
