"""
Web Search Tool - Provides web search capability for AI agents.
Supports multiple search backends (Tavily, Bing, etc.).
"""

import httpx
from typing import Optional, List, Dict, Any


class WebSearchTool:
    """
    Web search tool that can be used by agents to find real-time information.
    Currently supports Tavily search API.
    """

    def __init__(
        self,
        api_key: str,
        provider: str = "tavily",
        timeout: float = 30.0,
    ):
        """
        Initialize web search tool.

        Args:
            api_key: API key for the search provider
            provider: Search provider ("tavily")
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.provider = provider
        self.timeout = timeout

    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
    ) -> List[Dict[str, Any]]:
        """
        Perform a web search.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            search_depth: Search depth ("basic" or "advanced")

        Returns:
            List of search results, each containing 'title', 'url', 'content'
        """
        if self.provider == "tavily":
            return await self._search_tavily(query, max_results, search_depth)
        else:
            raise ValueError(f"Unsupported search provider: {self.provider}")

    async def _search_tavily(
        self,
        query: str,
        max_results: int,
        search_depth: str,
    ) -> List[Dict[str, Any]]:
        """Perform search using Tavily API."""
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
            })

        return results

    def format_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Format search results into a string for LLM context.

        Args:
            results: Search results

        Returns:
            Formatted string with search results
        """
        if not results:
            return "No search results found."

        formatted = "## Web Search Results\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"### {i}. {result['title']}\n"
            formatted += f"**URL**: {result['url']}\n"
            formatted += f"{result['content']}\n\n"

        return formatted
