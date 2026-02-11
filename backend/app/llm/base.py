"""
LLM Provider Base - Abstract base for all LLM API providers.
Supports multimodal messages (text + images).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
from dataclasses import dataclass, field


@dataclass
class LLMMessage:
    """
    Represents a message in a conversation.
    Supports multimodal content (text and images).
    """
    role: str  # "system", "user", "assistant"
    content: Union[str, List[Dict[str, Any]]]  # text or multimodal content blocks

    @staticmethod
    def text(role: str, text: str) -> "LLMMessage":
        """Create a text-only message."""
        return LLMMessage(role=role, content=text)

    @staticmethod
    def multimodal(role: str, text: str, image_urls: Optional[List[str]] = None,
                   image_base64_list: Optional[List[Dict[str, str]]] = None) -> "LLMMessage":
        """
        Create a multimodal message with text and images.

        Args:
            role: Message role
            text: Text content
            image_urls: List of image URLs
            image_base64_list: List of dicts with 'data' (base64 string) and 'media_type'
        """
        content_parts: List[Dict[str, Any]] = []

        # Add images first
        if image_urls:
            for url in image_urls:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })

        if image_base64_list:
            for img in image_base64_list:
                data_uri = f"data:{img['media_type']};base64,{img['data']}"
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": data_uri}
                })

        # Add text
        content_parts.append({"type": "text", "text": text})

        return LLMMessage(role=role, content=content_parts)


@dataclass
class LLMResponse:
    """Response from an LLM API call."""
    content: str
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    raw: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM API providers.
    All providers must implement chat_completion.
    """

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None,
                 default_temperature: float = 0.7, default_max_tokens: int = 2048):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Send a chat completion request.

        Args:
            messages: List of conversation messages (supports multimodal)
            temperature: Sampling temperature override
            max_tokens: Max tokens override
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with the generated content
        """
        pass

    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion tokens.

        Args:
            messages: List of conversation messages (supports multimodal)
            temperature: Sampling temperature override
            max_tokens: Max tokens override
            **kwargs: Additional provider-specific parameters

        Yields:
            str: Individual tokens/chunks from the LLM
        """
        pass

    def _format_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """Convert LLMMessage list to API-compatible format."""
        return [{"role": m.role, "content": m.content} for m in messages]
