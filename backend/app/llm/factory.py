"""
LLM Provider Factory - Creates the configured LLM provider instance.
"""

from typing import Optional
from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .volcengine_provider import VolcEngineProvider


def create_llm_provider(
    provider: str = "openai",
    api_key: str = "",
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> Optional[LLMProvider]:
    """
    Create an LLM provider instance based on configuration.

    Args:
        provider: Provider name ("openai" or "volcengine")
        api_key: API key for the provider
        model: Model name (uses provider default if not specified)
        base_url: Custom base URL (uses provider default if not specified)
        **kwargs: Additional provider-specific parameters

    Returns:
        LLMProvider instance, or None if api_key is not configured
    """
    if not api_key:
        return None

    if provider == "openai":
        params = {"api_key": api_key}
        if model:
            params["model"] = model
        if base_url:
            params["base_url"] = base_url
        params.update(kwargs)
        return OpenAIProvider(**params)

    elif provider == "volcengine":
        params = {"api_key": api_key}
        if model:
            params["model"] = model
        if base_url:
            params["base_url"] = base_url
        params.update(kwargs)
        return VolcEngineProvider(**params)

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
