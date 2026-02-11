"""
Feishu (Lark) Bot Integration.
Handles webhook events from Feishu including text messages, image uploads, and voice input.
"""

import base64
import hashlib
import hmac
import json
import logging
from typing import Dict, Any, Optional, List

import httpx

logger = logging.getLogger(__name__)


class FeishuBot:
    """
    Feishu (Lark) bot client for receiving and sending messages.
    Supports text messages, image uploads, and voice-to-text.
    """

    TENANT_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    SEND_MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"
    GET_RESOURCE_URL = "https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/resources/{file_key}"
    SPEECH_TO_TEXT_URL = "https://open.feishu.cn/open-apis/speech_to_text/v1/speech/stream_recognize"

    def __init__(self, app_id: str, app_secret: str,
                 verification_token: Optional[str] = None,
                 encrypt_key: Optional[str] = None):
        """
        Initialize Feishu bot.

        Args:
            app_id: Feishu app ID
            app_secret: Feishu app secret
            verification_token: Webhook verification token
            encrypt_key: Event encryption key
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key
        self._tenant_access_token: Optional[str] = None

    async def get_tenant_access_token(self) -> str:
        """Get or refresh tenant access token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                self.TENANT_TOKEN_URL,
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            resp.raise_for_status()
            data = resp.json()

        self._tenant_access_token = data["tenant_access_token"]
        return self._tenant_access_token

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with tenant access token."""
        return {
            "Authorization": f"Bearer {self._tenant_access_token}",
            "Content-Type": "application/json",
        }

    async def send_text_message(self, chat_id: str, text: str,
                                receive_id_type: str = "chat_id") -> Dict[str, Any]:
        """
        Send a text message to a Feishu chat.

        Args:
            chat_id: Target chat ID (or open_id / user_id)
            text: Message text
            receive_id_type: Type of receive_id ("chat_id", "open_id", "user_id")
        """
        if not self._tenant_access_token:
            await self.get_tenant_access_token()

        url = f"{self.SEND_MESSAGE_URL}?receive_id_type={receive_id_type}"
        payload = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=self._get_auth_headers())
            resp.raise_for_status()
            return resp.json()

    async def download_image(self, message_id: str, file_key: str) -> bytes:
        """
        Download an image from a Feishu message.

        Args:
            message_id: Message ID containing the image
            file_key: Image file key

        Returns:
            Image bytes
        """
        if not self._tenant_access_token:
            await self.get_tenant_access_token()

        url = self.GET_RESOURCE_URL.format(message_id=message_id, file_key=file_key)
        params = {"type": "image"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url, params=params, headers=self._get_auth_headers())
            resp.raise_for_status()
            return resp.content

    async def download_audio(self, message_id: str, file_key: str) -> bytes:
        """
        Download audio from a Feishu voice message.

        Args:
            message_id: Message ID containing the audio
            file_key: Audio file key

        Returns:
            Audio bytes
        """
        if not self._tenant_access_token:
            await self.get_tenant_access_token()

        url = self.GET_RESOURCE_URL.format(message_id=message_id, file_key=file_key)
        params = {"type": "file"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url, params=params, headers=self._get_auth_headers())
            resp.raise_for_status()
            return resp.content

    async def speech_to_text(self, audio_data: bytes,
                             speech_format: str = "opus") -> str:
        """
        Convert speech audio to text using Feishu API.

        Args:
            audio_data: Audio data bytes
            speech_format: Audio format ("opus", "pcm", "ogg")

        Returns:
            Transcribed text
        """
        if not self._tenant_access_token:
            await self.get_tenant_access_token()

        payload = {
            "speech": {
                "speech": base64.b64encode(audio_data).decode("utf-8"),
            },
            "config": {
                "format": speech_format,
                "engine_type": "16k_auto",
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self.SPEECH_TO_TEXT_URL, json=payload, headers=self._get_auth_headers()
            )
            resp.raise_for_status()
            data = resp.json()

        return data.get("data", {}).get("recognition_text", "")

    def verify_signature(self, timestamp: str, nonce: str,
                         body: str, signature: str) -> bool:
        """
        Verify the webhook event signature.

        Args:
            timestamp: Timestamp from header
            nonce: Nonce from header
            body: Raw request body
            signature: Signature from header

        Returns:
            True if signature is valid
        """
        if not self.encrypt_key:
            return True

        content = timestamp + nonce + self.encrypt_key + body
        computed = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return hmac.compare_digest(computed, signature)

    @staticmethod
    def parse_event(body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a Feishu webhook event body into a standardized format.

        Args:
            body: Raw event body from Feishu webhook

        Returns:
            Parsed event with type, message content, sender info, etc.
        """
        # URL verification challenge
        if "challenge" in body:
            return {"type": "url_verification", "challenge": body["challenge"]}

        schema_version = body.get("schema", "1.0")
        header = body.get("header", {})
        event = body.get("event", {})
        event_type = header.get("event_type", body.get("type", ""))

        # Handle v2.0 message events
        if event_type == "im.message.receive_v1":
            message = event.get("message", {})
            sender = event.get("sender", {})
            msg_type = message.get("message_type", "text")
            chat_id = message.get("chat_id", "")
            message_id = message.get("message_id", "")

            parsed = {
                "type": "message",
                "message_type": msg_type,
                "chat_id": chat_id,
                "message_id": message_id,
                "sender_id": sender.get("sender_id", {}).get("open_id", ""),
                "sender_type": sender.get("sender_type", ""),
            }

            # Parse message content based on type
            content_str = message.get("content", "{}")
            try:
                content = json.loads(content_str)
            except json.JSONDecodeError:
                content = {}

            if msg_type == "text":
                parsed["text"] = content.get("text", "")
            elif msg_type == "image":
                parsed["image_key"] = content.get("image_key", "")
            elif msg_type == "audio":
                parsed["file_key"] = content.get("file_key", "")
                parsed["duration"] = content.get("duration", 0)

            return parsed

        return {"type": "unknown", "event_type": event_type, "raw": body}
