"""
LLM Factory for creating language model instances from different providers.
Supports Claude (Anthropic), Ollama, and OpenAI.
"""

import os
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel


def create_llm(
    provider: str,
    model: str,
    temperature: float = 0.7,
    **kwargs
) -> BaseChatModel:
    """
    Create an LLM instance based on the provider.

    Args:
        provider: The LLM provider ("claude", "ollama", "openai")
        model: The model name/identifier
        temperature: Sampling temperature (default 0.7)
        **kwargs: Additional provider-specific arguments

    Returns:
        BaseChatModel: The configured LLM instance

    Raises:
        ValueError: If the provider is not supported
    """
    provider = provider.lower()

    if provider == "claude":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model,
            temperature=temperature,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            **kwargs
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model,
            temperature=temperature,
            **kwargs
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY"),
            **kwargs
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers: claude, ollama, openai"
        )


def create_llm_from_config(config) -> BaseChatModel:
    """
    Create an LLM instance from an AgentConfig.

    Args:
        config: AgentConfig instance with llm_provider, model, and temperature

    Returns:
        BaseChatModel: The configured LLM instance
    """
    return create_llm(
        provider=config.llm_provider,
        model=config.model,
        temperature=config.temperature
    )
