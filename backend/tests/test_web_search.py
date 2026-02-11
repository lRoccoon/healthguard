"""
Unit tests for Web Search tool.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.tools.web_search import WebSearchTool


class TestWebSearchTool:
    """Tests for WebSearchTool."""

    def test_init(self):
        tool = WebSearchTool(api_key="test-key", provider="tavily")
        assert tool.api_key == "test-key"
        assert tool.provider == "tavily"

    @pytest.mark.asyncio
    async def test_search_tavily(self):
        tool = WebSearchTool(api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Low GI Foods",
                    "url": "https://example.com/low-gi",
                    "content": "List of low GI foods for diabetes.",
                },
                {
                    "title": "Insulin Resistance Diet",
                    "url": "https://example.com/ir-diet",
                    "content": "Diet tips for insulin resistance.",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            results = await tool.search("low GI foods for insulin resistance")
            assert len(results) == 2
            assert results[0]["title"] == "Low GI Foods"
            assert results[1]["url"] == "https://example.com/ir-diet"

    @pytest.mark.asyncio
    async def test_search_unsupported_provider(self):
        tool = WebSearchTool(api_key="key", provider="unsupported")
        with pytest.raises(ValueError, match="Unsupported"):
            await tool.search("test query")

    def test_format_results(self):
        tool = WebSearchTool(api_key="test-key")
        results = [
            {"title": "Result 1", "url": "https://example.com/1", "content": "Content 1"},
            {"title": "Result 2", "url": "https://example.com/2", "content": "Content 2"},
        ]
        formatted = tool.format_results(results)
        assert "Result 1" in formatted
        assert "Result 2" in formatted
        assert "https://example.com/1" in formatted

    def test_format_results_empty(self):
        tool = WebSearchTool(api_key="test-key")
        formatted = tool.format_results([])
        assert "No search results" in formatted
