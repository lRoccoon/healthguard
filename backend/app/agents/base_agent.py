"""
Base Agent Class - Abstract base for all AI agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..llm.base import LLMProvider, LLMMessage, LLMResponse


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
            return response.content
        except Exception as e:
            return f"[LLM call failed for {self.name}: {e}]"
