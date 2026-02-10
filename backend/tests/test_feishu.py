"""
Unit tests for Feishu channel integration.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.channels.feishu import FeishuBot


class TestFeishuBot:
    """Tests for FeishuBot client."""

    def test_init(self):
        bot = FeishuBot(
            app_id="test_id",
            app_secret="test_secret",
            verification_token="test_token",
            encrypt_key="test_key",
        )
        assert bot.app_id == "test_id"
        assert bot.app_secret == "test_secret"
        assert bot.verification_token == "test_token"

    def test_verify_signature_no_encrypt_key(self):
        bot = FeishuBot(app_id="id", app_secret="secret")
        assert bot.verify_signature("ts", "nonce", "body", "sig") is True

    def test_verify_signature_valid(self):
        import hashlib
        encrypt_key = "test_key"
        timestamp = "12345"
        nonce = "abc"
        body = '{"data": "test"}'

        content = timestamp + nonce + encrypt_key + body
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()

        bot = FeishuBot(app_id="id", app_secret="secret", encrypt_key=encrypt_key)
        assert bot.verify_signature(timestamp, nonce, body, expected) is True

    def test_verify_signature_invalid(self):
        bot = FeishuBot(app_id="id", app_secret="secret", encrypt_key="key")
        assert bot.verify_signature("ts", "nonce", "body", "wrong_sig") is False


class TestFeishuEventParsing:
    """Tests for Feishu event parsing."""

    def test_url_verification(self):
        body = {"challenge": "test_challenge_token"}
        result = FeishuBot.parse_event(body)
        assert result["type"] == "url_verification"
        assert result["challenge"] == "test_challenge_token"

    def test_text_message_event(self):
        body = {
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
                "event_id": "evt_123",
            },
            "event": {
                "message": {
                    "message_type": "text",
                    "chat_id": "oc_test",
                    "message_id": "msg_123",
                    "content": json.dumps({"text": "你好"}),
                },
                "sender": {
                    "sender_id": {"open_id": "ou_user1"},
                    "sender_type": "user",
                },
            },
        }
        result = FeishuBot.parse_event(body)
        assert result["type"] == "message"
        assert result["message_type"] == "text"
        assert result["text"] == "你好"
        assert result["chat_id"] == "oc_test"
        assert result["sender_id"] == "ou_user1"

    def test_image_message_event(self):
        body = {
            "schema": "2.0",
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "message_type": "image",
                    "chat_id": "oc_test",
                    "message_id": "msg_456",
                    "content": json.dumps({"image_key": "img_key_123"}),
                },
                "sender": {
                    "sender_id": {"open_id": "ou_user1"},
                    "sender_type": "user",
                },
            },
        }
        result = FeishuBot.parse_event(body)
        assert result["type"] == "message"
        assert result["message_type"] == "image"
        assert result["image_key"] == "img_key_123"

    def test_audio_message_event(self):
        body = {
            "schema": "2.0",
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "message_type": "audio",
                    "chat_id": "oc_test",
                    "message_id": "msg_789",
                    "content": json.dumps({"file_key": "file_key_123", "duration": 5000}),
                },
                "sender": {
                    "sender_id": {"open_id": "ou_user1"},
                    "sender_type": "user",
                },
            },
        }
        result = FeishuBot.parse_event(body)
        assert result["type"] == "message"
        assert result["message_type"] == "audio"
        assert result["file_key"] == "file_key_123"

    def test_unknown_event(self):
        body = {
            "schema": "2.0",
            "header": {"event_type": "some.unknown.event"},
            "event": {},
        }
        result = FeishuBot.parse_event(body)
        assert result["type"] == "unknown"


class TestFeishuBotAPI:
    """Tests for FeishuBot API calls."""

    @pytest.mark.asyncio
    async def test_get_tenant_access_token(self):
        bot = FeishuBot(app_id="test_id", app_secret="test_secret")

        mock_response = MagicMock()
        mock_response.json.return_value = {"tenant_access_token": "t-token123"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            token = await bot.get_tenant_access_token()
            assert token == "t-token123"
            assert bot._tenant_access_token == "t-token123"

    @pytest.mark.asyncio
    async def test_send_text_message(self):
        bot = FeishuBot(app_id="test_id", app_secret="test_secret")
        bot._tenant_access_token = "t-token"

        mock_response = MagicMock()
        mock_response.json.return_value = {"code": 0, "msg": "ok"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await bot.send_text_message("oc_chat1", "Hello")
            assert result["code"] == 0

    @pytest.mark.asyncio
    async def test_speech_to_text(self):
        bot = FeishuBot(app_id="test_id", app_secret="test_secret")
        bot._tenant_access_token = "t-token"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"recognition_text": "你好世界"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            text = await bot.speech_to_text(b"audio_data")
            assert text == "你好世界"
