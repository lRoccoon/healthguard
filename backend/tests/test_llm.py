"""
Unit tests for the LLM module.
Tests LLMMessage, LLMResponse, providers, and factory.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from app.llm.base import LLMMessage, LLMResponse, LLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.volcengine_provider import VolcEngineProvider
from app.llm.factory import create_llm_provider


class TestLLMMessage:
    """Tests for LLMMessage dataclass."""

    def test_text_message(self):
        msg = LLMMessage.text("user", "Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_system_message(self):
        msg = LLMMessage.text("system", "You are a helpful assistant")
        assert msg.role == "system"
        assert msg.content == "You are a helpful assistant"

    def test_multimodal_with_image_url(self):
        msg = LLMMessage.multimodal("user", "What is this?",
                                     image_urls=["https://example.com/img.jpg"])
        assert msg.role == "user"
        assert isinstance(msg.content, list)
        assert len(msg.content) == 2
        assert msg.content[0]["type"] == "image_url"
        assert msg.content[0]["image_url"]["url"] == "https://example.com/img.jpg"
        assert msg.content[1]["type"] == "text"
        assert msg.content[1]["text"] == "What is this?"

    def test_multimodal_with_base64_image(self):
        msg = LLMMessage.multimodal("user", "Analyze",
                                     image_base64_list=[{
                                         "data": "abc123",
                                         "media_type": "image/jpeg"
                                     }])
        assert isinstance(msg.content, list)
        assert len(msg.content) == 2
        img_part = msg.content[0]
        assert img_part["type"] == "image_url"
        assert img_part["image_url"]["url"] == "data:image/jpeg;base64,abc123"

    def test_multimodal_with_multiple_images(self):
        msg = LLMMessage.multimodal("user", "Compare these",
                                     image_urls=["url1", "url2"])
        assert len(msg.content) == 3  # 2 images + 1 text

    def test_multimodal_text_only(self):
        msg = LLMMessage.multimodal("user", "Just text")
        assert isinstance(msg.content, list)
        assert len(msg.content) == 1
        assert msg.content[0]["type"] == "text"


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_basic_response(self):
        resp = LLMResponse(content="Hello!", model="gpt-4")
        assert resp.content == "Hello!"
        assert resp.model == "gpt-4"
        assert resp.usage == {}
        assert resp.raw is None

    def test_response_with_usage(self):
        resp = LLMResponse(
            content="Hi",
            model="test",
            usage={"prompt_tokens": 10, "completion_tokens": 5}
        )
        assert resp.usage["prompt_tokens"] == 10


class TestOpenAIProvider:
    """Tests for OpenAI-compatible provider."""

    def test_init_defaults(self):
        provider = OpenAIProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.model == "gpt-4o"
        assert provider.base_url == "https://api.openai.com/v1"

    def test_init_custom(self):
        provider = OpenAIProvider(
            api_key="key",
            model="gpt-3.5-turbo",
            base_url="https://custom.api.com/v1"
        )
        assert provider.model == "gpt-3.5-turbo"
        assert provider.base_url == "https://custom.api.com/v1"

    def test_format_messages(self):
        provider = OpenAIProvider(api_key="test")
        messages = [
            LLMMessage.text("system", "sys prompt"),
            LLMMessage.text("user", "hello")
        ]
        formatted = provider._format_messages(messages)
        assert len(formatted) == 2
        assert formatted[0] == {"role": "system", "content": "sys prompt"}
        assert formatted[1] == {"role": "user", "content": "hello"}

    def test_headers(self):
        provider = OpenAIProvider(api_key="sk-test123")
        headers = provider._get_headers()
        assert headers["Authorization"] == "Bearer sk-test123"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_chat_completion_success(self):
        provider = OpenAIProvider(api_key="test-key")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}],
            "model": "gpt-4o",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await provider.chat_completion(
                [LLMMessage.text("user", "Hello")]
            )

            assert result.content == "Test response"
            assert result.model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_responses_api_success(self):
        provider = OpenAIProvider(api_key="test-key")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Response text"}]
                }
            ],
            "model": "gpt-4o",
            "usage": {}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await provider.responses(
                [LLMMessage.text("user", "Hello")]
            )

            assert result.content == "Response text"


class TestVolcEngineProvider:
    """Tests for Volcano Engine provider."""

    def test_init_defaults(self):
        provider = VolcEngineProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.model == "doubao-1-5-pro-256k-250115"
        assert "volces.com" in provider.base_url

    def test_init_custom(self):
        provider = VolcEngineProvider(
            api_key="key",
            model="custom-model",
            base_url="https://custom.volces.com/api/v3"
        )
        assert provider.model == "custom-model"

    @pytest.mark.asyncio
    async def test_chat_completion_success(self):
        provider = VolcEngineProvider(api_key="test-key")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "火山引擎回复"}}],
            "model": "doubao-1-5-pro-256k-250115",
            "usage": {}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await provider.chat_completion(
                [LLMMessage.text("user", "你好")]
            )

            assert result.content == "火山引擎回复"


class TestLLMFactory:
    """Tests for LLM provider factory."""

    def test_create_openai_provider(self):
        provider = create_llm_provider(
            provider="openai",
            api_key="test-key",
            model="gpt-4o"
        )
        assert isinstance(provider, OpenAIProvider)
        assert provider.model == "gpt-4o"

    def test_create_volcengine_provider(self):
        provider = create_llm_provider(
            provider="volcengine",
            api_key="test-key"
        )
        assert isinstance(provider, VolcEngineProvider)

    def test_no_api_key_returns_none(self):
        provider = create_llm_provider(provider="openai", api_key="")
        assert provider is None

    def test_unsupported_provider_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            create_llm_provider(provider="unsupported", api_key="key")

    def test_custom_base_url(self):
        provider = create_llm_provider(
            provider="openai",
            api_key="key",
            base_url="https://custom.api.com/v1"
        )
        assert provider.base_url == "https://custom.api.com/v1"
