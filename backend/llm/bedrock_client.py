"""LLM factory using user-managed OpenAI-compatible model configs."""

from typing import Optional
from langchain_openai import ChatOpenAI
from config import get_settings
from services.config_registry import config_registry

settings = get_settings()


def get_llm(model_id: Optional[str] = None, temperature: float = 0.7, purpose: Optional[str] = None) -> ChatOpenAI:
    """
    Get a configured ChatOpenAI instance for Bedrock.

    Args:
        model_id: Model ID (defaults to settings.LLM_MODEL_ID)
        temperature: Sampling temperature

    Returns:
        Configured ChatOpenAI instance
    """
    config = config_registry.get_model(purpose) if purpose else None
    model = model_id or (config.model if config else settings.LLM_MODEL_ID)
    api_key = (config.api_key if config else None) or settings.OPENAI_API_KEY or settings.BEDROCK_KEY or settings.AWS_SECRET_ACCESS_KEY
    base_url = (config.base_url if config else None) or settings.OPENAI_BASE_URL or settings.BEDROCK_URL
    llm_temperature = config.temperature if config and temperature == 0.7 else temperature
    kwargs = {}
    if config and config.max_tokens:
        kwargs["max_tokens"] = config.max_tokens
    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=llm_temperature,
        **kwargs,
    )


def get_llm_for_purpose(purpose: str) -> ChatOpenAI:
    """Build an LLM from the in-memory purpose config."""
    config = config_registry.get_model(purpose)
    return get_llm(model_id=config.model, temperature=config.temperature, purpose=purpose)


class LazyLLM:
    def invoke(self, *args, **kwargs):
        return get_llm().invoke(*args, **kwargs)


llm = LazyLLM()
