"""
Volcano Engine (火山引擎) LLM Provider.
Supports both Chat Completions and Responses API endpoints.
Uses OpenAI-compatible API format with Volcano Engine's authentication.
"""

import httpx
from typing import Optional, List, Dict, Any

from .base import LLMProvider, LLMMessage, LLMResponse


class VolcEngineProvider(LLMProvider):
    """
    Provider for Volcano Engine (火山引擎) Doubao / Ark API.
    Compatible with OpenAI-style chat/completions endpoint.
    Default base_url points to the Volcano Engine Ark API.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "doubao-1-5-pro-256k-250115",
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        default_temperature: float = 0.7,
        default_max_tokens: int = 2048,
        timeout: float = 120.0,
    ):
        super().__init__(api_key, model, base_url, default_temperature, default_max_tokens)
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Send request to the Chat Completions endpoint."""
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": self._format_messages(messages),
            "temperature": temperature if temperature is not None else self.default_temperature,
            "max_tokens": max_tokens or self.default_max_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=self._get_headers())
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            raw=data,
        )

    async def responses(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Send request to the Responses API endpoint.
        Volcano Engine's Ark API also supports the responses-style endpoint.
        """
        url = f"{self.base_url}/responses"

        input_items = []
        for msg in messages:
            item: Dict[str, Any] = {"role": msg.role}
            if isinstance(msg.content, str):
                item["content"] = msg.content
            else:
                item["content"] = msg.content
            input_items.append(item)

        payload: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "input": input_items,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        else:
            payload["temperature"] = self.default_temperature
        if max_tokens:
            payload["max_output_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=self._get_headers())
            resp.raise_for_status()
            data = resp.json()

        # Extract text from response output
        content = ""
        for item in data.get("output", []):
            if item.get("type") == "message":
                for block in item.get("content", []):
                    if block.get("type") == "output_text":
                        content += block.get("text", "")

        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            raw=data,
        )
