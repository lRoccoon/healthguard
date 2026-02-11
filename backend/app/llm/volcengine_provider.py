"""
Volcano Engine (火山引擎) LLM Provider.
Supports both Chat Completions and Responses API endpoints.
Uses OpenAI-compatible API format with Volcano Engine's authentication.
"""

import httpx
import json
import logging
import time
from typing import Optional, List, Dict, Any, AsyncGenerator

from .base import LLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class VolcEngineProvider(LLMProvider):
    """
    Provider for Volcano Engine (火山引擎) Doubao / Ark API.
    Compatible with OpenAI-style chat/completions endpoint.
    Default base_url points to the Volcano Engine Ark API.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "kimi-k2.5",
        base_url: str = "https://ark.cn-beijing.volces.com/api/coding/v3",
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
        start_time = time.time()
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": self._format_messages(messages),
            "temperature": temperature if temperature is not None else self.default_temperature,
            "max_tokens": max_tokens or self.default_max_tokens,
        }

        # Log request (DEBUG level)
        if logger.isEnabledFor(logging.DEBUG):
            message_summary = f"{len(messages)} messages"
            if messages:
                first_msg = str(messages[0].content)[:200] if messages[0].content else ""
                message_summary += f", first: {first_msg}"
            logger.debug(
                f"LLM API call starting: provider=volcengine, model={payload['model']}, "
                f"temperature={payload['temperature']}, {message_summary}"
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=self._get_headers())
                logger.debug(f"LLM API response status: {resp.status_code}, response: {resp.text}")
                resp.raise_for_status()
                data = resp.json()

            choice = data["choices"][0]
            usage = data.get("usage", {})
            duration_ms = (time.time() - start_time) * 1000

            # Log successful response (INFO level)
            logger.info(
                f"LLM API call completed",
                extra={"extra_fields": {
                    "provider": "volcengine",
                    "model": data.get("model", self.model),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "duration_ms": round(duration_ms, 2),
                }}
            )

            return LLMResponse(
                content=choice["message"]["content"],
                model=data.get("model", self.model),
                usage=usage,
                raw=data,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"LLM API call failed: {str(e)}",
                exc_info=True,
                extra={"extra_fields": {
                    "provider": "volcengine",
                    "model": payload.get("model"),
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                }}
            )
            raise

    async def chat_completion_stream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion tokens from the Chat Completions endpoint."""
        start_time = time.time()
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": self._format_messages(messages),
            "temperature": temperature if temperature is not None else self.default_temperature,
            "max_tokens": max_tokens or self.default_max_tokens,
            "stream": True,
        }

        # Log request (DEBUG level)
        if logger.isEnabledFor(logging.DEBUG):
            message_summary = f"{len(messages)} messages"
            if messages:
                first_msg = str(messages[0].content)[:200] if messages[0].content else ""
                message_summary += f", first: {first_msg}"
            logger.debug(
                f"LLM API stream starting: provider=volcengine, model={payload['model']}, "
                f"temperature={payload['temperature']}, {message_summary}"
            )

        accumulated_content = ""
        usage_data = {}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream('POST', url, json=payload, headers=self._get_headers()) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        # Skip empty lines
                        if not line or line.strip() == "":
                            continue

                        # SSE format: "data: {json}" or "data: [DONE]"
                        if line.startswith("data: "):
                            data_str = line[6:].strip()

                            # Check for stream end
                            if data_str == "[DONE]":
                                break

                            try:
                                chunk = json.loads(data_str)

                                # Extract content delta
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    choice = chunk["choices"][0]
                                    delta = choice.get("delta", {})
                                    content = delta.get("content")

                                    if content:
                                        accumulated_content += content
                                        yield content

                                # Capture usage data if present (typically in last chunk)
                                if chunk.get("usage"):
                                    usage_data = chunk["usage"]

                            except json.JSONDecodeError:
                                # Skip malformed chunks
                                continue

            duration_ms = (time.time() - start_time) * 1000

            # Log successful stream completion (INFO level)
            logger.info(
                f"LLM API stream completed",
                extra={"extra_fields": {
                    "provider": "volcengine",
                    "model": payload.get("model", self.model),
                    "prompt_tokens": usage_data.get("prompt_tokens", 0),
                    "completion_tokens": usage_data.get("completion_tokens", 0),
                    "total_tokens": usage_data.get("total_tokens", 0),
                    "duration_ms": round(duration_ms, 2),
                    "content_length": len(accumulated_content),
                }}
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"LLM API stream failed: {str(e)}",
                exc_info=True,
                extra={"extra_fields": {
                    "provider": "volcengine",
                    "model": payload.get("model"),
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                }}
            )
            raise

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
        start_time = time.time()
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

        # Log request (DEBUG level)
        if logger.isEnabledFor(logging.DEBUG):
            message_summary = f"{len(messages)} messages"
            if messages:
                first_msg = str(messages[0].content)[:200] if messages[0].content else ""
                message_summary += f", first: {first_msg}"
            logger.debug(
                f"LLM API call starting (responses API): provider=volcengine, model={payload['model']}, "
                f"temperature={payload['temperature']}, {message_summary}"
            )

        try:
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

            usage = data.get("usage", {})
            duration_ms = (time.time() - start_time) * 1000

            # Log successful response (INFO level)
            logger.info(
                f"LLM API call completed (responses API)",
                extra={"extra_fields": {
                    "provider": "volcengine",
                    "model": data.get("model", self.model),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "duration_ms": round(duration_ms, 2),
                }}
            )

            return LLMResponse(
                content=content,
                model=data.get("model", self.model),
                usage=usage,
                raw=data,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"LLM API call failed (responses API): {str(e)}",
                exc_info=True,
                extra={"extra_fields": {
                    "provider": "volcengine",
                    "model": payload.get("model"),
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                }}
            )
            raise
