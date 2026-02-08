"""
Base Agent Class - Abstract base for all AI agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


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
        temperature: float = 0.7
    ) -> str:
        """
        Call LLM API (placeholder for Phase 3 implementation).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Temperature for generation
            
        Returns:
            LLM response text
        """
        # TODO: Implement actual LLM call (OpenAI, Anthropic, etc.)
        # For now, return a placeholder
        return f"[Placeholder response from {self.name}. LLM integration will be implemented in Phase 3 with actual API keys.]"
