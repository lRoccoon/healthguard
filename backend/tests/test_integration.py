"""
Integration tests for the chat API flow.
Tests the full message processing pipeline.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.utils.auth import create_access_token, create_user_in_db, get_password_hash


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create a test user and return auth headers."""
    # Run async function in sync context for fixture
    user = asyncio.run(create_user_in_db(
        username="testuser_integration",
        hashed_password=get_password_hash("testpass123"),
    ))
    token = create_access_token(
        data={"sub": user["user_id"], "username": user["username"]}
    )
    return {"Authorization": f"Bearer {token}"}


class TestChatAPIIntegration:
    """Integration tests for chat endpoints."""

    def test_send_message_text(self, client, auth_headers):
        """Test sending a text message through the chat API."""
        response = client.post(
            "/chat/message",
            json={
                "role": "user",
                "content": "你好",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "assistant"
        assert len(data["content"]) > 0

    def test_send_message_diet_routing(self, client, auth_headers):
        """Test that food-related messages route to diet agent."""
        response = client.post(
            "/chat/message",
            json={
                "role": "user",
                "content": "I ate rice and chicken for lunch, analyze my meal",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "assistant"
        # Response should contain diet-related content
        assert len(data["content"]) > 0

    def test_send_message_fitness_routing(self, client, auth_headers):
        """Test that fitness-related messages route to fitness agent."""
        response = client.post(
            "/chat/message",
            json={
                "role": "user",
                "content": "I walked 10000 steps today during my exercise",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "assistant"

    def test_send_message_unauthorized(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.post(
            "/chat/message",
            json={"role": "user", "content": "Hello"},
        )
        assert response.status_code == 403

    def test_chat_history(self, client, auth_headers):
        """Test getting chat history."""
        response = client.get("/chat/history", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestMessageWithImageIntegration:
    """Integration tests for image upload endpoint."""

    def test_send_message_with_image(self, client, auth_headers):
        """Test sending a message with an image."""
        # Create a small test image (1x1 PNG)
        import base64
        # Minimal valid PNG
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
            "nGNgYPgPAAEDAQAIicLsAAAAASUVORK5CYII="
        )

        response = client.post(
            "/chat/message-with-image",
            data={"content": "What food is in this image?"},
            files=[("images", ("test.png", png_data, "image/png"))],
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "assistant"

    def test_send_message_without_image(self, client, auth_headers):
        """Test sending text-only through image endpoint."""
        response = client.post(
            "/chat/message-with-image",
            data={"content": "Hello, just text"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "assistant"

    def test_send_message_with_unsupported_file_type(self, client, auth_headers):
        """Test that unsupported file types are rejected."""
        response = client.post(
            "/chat/message-with-image",
            data={"content": "Check this file"},
            files=[("images", ("test.txt", b"hello", "text/plain"))],
            headers=auth_headers,
        )
        assert response.status_code == 400


class TestFeishuWebhookIntegration:
    """Integration tests for Feishu webhook endpoint."""

    def test_feishu_not_configured(self, client):
        """Test that webhook returns 503 when Feishu is not configured."""
        response = client.post(
            "/feishu/webhook",
            json={"challenge": "test"},
        )
        assert response.status_code == 503

    @patch("app.api.feishu_webhook.settings")
    def test_feishu_url_verification(self, mock_settings, client):
        """Test Feishu URL verification challenge."""
        mock_settings.feishu_app_id = "test_id"
        mock_settings.feishu_app_secret = "test_secret"
        mock_settings.feishu_verification_token = "test_token"
        mock_settings.feishu_encrypt_key = None
        mock_settings.llm_api_key = None
        mock_settings.openai_api_key = None
        mock_settings.llm_provider = "openai"
        mock_settings.llm_model = None
        mock_settings.llm_base_url = None
        mock_settings.llm_api_mode = "chat"
        mock_settings.local_storage_path = "/tmp/healthguard_test"

        response = client.post(
            "/feishu/webhook",
            json={"challenge": "verification_challenge_token"},
        )
        assert response.status_code == 200
        assert response.json()["challenge"] == "verification_challenge_token"


class TestAppEndpoints:
    """Tests for basic app endpoints."""

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["app"] == "HealthGuard AI"
        assert data["status"] == "running"

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
