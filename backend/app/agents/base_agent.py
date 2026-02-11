"""
Base Agent Class - Abstract base for all AI agents.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime

from ..llm.base import LLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents.
    Each agent should implement process_request method.
    """

    def __init__(self, name: str, system_prompt: str):
        """
        Initialize base agent.
        
        Args:
            name: Agent name
            system_prompt: System prompt for the agent
        """
        self.name = name
        self.system_prompt = system_prompt
        self.created_at = datetime.now()
        self._llm_provider: Optional[LLMProvider] = None
        self._api_mode: str = "chat"  # "chat" or "responses"

    def set_llm_provider(self, provider: LLMProvider, api_mode: str = "chat") -> None:
        """
        Set the LLM provider for this agent.
        
        Args:
            provider: LLM provider instance
            api_mode: "chat" for chat/completions, "responses" for responses API
        """
        self._llm_provider = provider
        self._api_mode = api_mode

    @abstractmethod
    async def process_request(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user request.
        
        Args:
            user_message: User's message
            context: Optional context including user history, preferences, etc.
            
        Returns:
            Dict containing response and any metadata
        """
        pass

    def format_context(self, context: Optional[Dict[str, Any]]) -> str:
        """
        Format context into a string for prompt injection.
        
        Args:
            context: Context dictionary
            
        Returns:
            Formatted context string
        """
        if not context:
            return ""
        
        formatted = "\n## User Context\n"
        
        if "user_history" in context:
            formatted += f"### Recent History\n{context['user_history']}\n\n"
        
        if "preferences" in context:
            formatted += f"### Preferences\n{context['preferences']}\n\n"
        
        if "health_data" in context:
            formatted += f"### Health Data\n{context['health_data']}\n\n"
        
        return formatted

    async def call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        image_base64_list: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Call LLM API. Uses the configured provider or returns a placeholder.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Temperature for generation
            image_base64_list: Optional list of dicts with 'data' and 'media_type'

        Returns:
            LLM response text
        """
        if self._llm_provider is None:
            return (
                f"[LLM not configured for {self.name}. "
                f"Set LLM_API_KEY and LLM_PROVIDER in environment to enable AI responses.]"
            )

        # Log LLM call start (DEBUG level)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Agent {self.name} calling LLM: {len(messages)} messages, "
                f"temperature={temperature}, has_images={bool(image_base64_list)}"
            )

        # Convert dict messages to LLMMessage objects
        llm_messages: List[LLMMessage] = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            # Attach images to the last user message
            if (role == "user" and image_base64_list
                    and msg is messages[-1]):
                llm_messages.append(
                    LLMMessage.multimodal(role, content, image_base64_list=image_base64_list)
                )
            else:
                llm_messages.append(LLMMessage.text(role, content))

        try:
            if self._api_mode == "responses" and hasattr(self._llm_provider, "responses"):
                response = await self._llm_provider.responses(
                    llm_messages, temperature=temperature
                )
            else:
                response = await self._llm_provider.chat_completion(
                    llm_messages, temperature=temperature
                )

            # Log response (DEBUG level)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"Agent {self.name} received LLM response: length={len(response.content)} chars"
                )

            return response.content
        except Exception as e:
            logger.error(
                f"Agent {self.name} LLM call failed: {str(e)}",
                exc_info=True,
                extra={"extra_fields": {"agent": self.name, "error": str(e)}}
            )
            return f"[LLM call failed for {self.name}: {e}]"

    async def call_llm_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        image_base64_list: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Call LLM API with streaming. Yields tokens as they arrive.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Temperature for generation
            image_base64_list: Optional list of dicts with 'data' and 'media_type'

        Yields:
            str: Individual tokens/chunks from the LLM
        """
        if self._llm_provider is None:
            yield (
                f"[LLM not configured for {self.name}. "
                f"Set LLM_API_KEY and LLM_PROVIDER in environment to enable AI responses.]"
            )
            return

        # Log LLM stream call start (DEBUG level)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Agent {self.name} calling LLM stream: {len(messages)} messages, "
                f"temperature={temperature}, has_images={bool(image_base64_list)}"
            )

        # Convert dict messages to LLMMessage objects
        llm_messages: List[LLMMessage] = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            # Attach images to the last user message
            if (role == "user" and image_base64_list
                    and msg is messages[-1]):
                llm_messages.append(
                    LLMMessage.multimodal(role, content, image_base64_list=image_base64_list)
                )
            else:
                llm_messages.append(LLMMessage.text(role, content))

        try:
            # Check if provider supports streaming
            if not hasattr(self._llm_provider, 'chat_completion_stream'):
                # Fallback to non-streaming if not supported
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        f"Agent {self.name}: Provider doesn't support streaming, falling back to non-streaming"
                    )
                response_text = await self.call_llm(messages, temperature, image_base64_list)
                yield response_text
                return

            # Use streaming
            accumulated_content = ""
            async for token in self._llm_provider.chat_completion_stream(
                llm_messages, temperature=temperature
            ):
                accumulated_content += token
                yield token

            # Log response (DEBUG level)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"Agent {self.name} completed LLM stream: length={len(accumulated_content)} chars"
                )

        except Exception as e:
            logger.error(
                f"Agent {self.name} LLM stream failed: {str(e)}",
                exc_info=True,
                extra={"extra_fields": {"agent": self.name, "error": str(e)}}
            )
            yield f"[LLM stream failed for {self.name}: {e}]"

