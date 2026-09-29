"""
Dedicated LLM provider module.

This is the ONLY place in the application that instantiates a chat model.
Instances are cached per temperature, so the rest of the app never builds
the model repeatedly. Adding another provider later means changing this
file only.
"""

import logging
from functools import lru_cache
from typing import Optional

from langchain_openai import ChatOpenAI

from app.config.settings import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=8)
def get_chat_model(temperature: Optional[float] = None) -> ChatOpenAI:
    """Return a cached ChatOpenAI for the given temperature (default: settings)."""
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is not set. LLM calls will fail until it is configured.")

    kwargs = {}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url

    return ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.temperature if temperature is None else temperature,
        # A placeholder keeps client construction from failing; real calls
        # without a key are rejected by the API and surface as a 502.
        api_key=settings.openai_api_key or "missing-api-key",
        timeout=settings.llm_request_timeout,
        max_retries=settings.llm_max_retries,
        **kwargs,
    )


def create_chat_model(temperature: Optional[float] = None) -> ChatOpenAI:
    """Backward-compatible alias for get_chat_model."""
    return get_chat_model(temperature)


def clear_model_cache() -> None:
    """Drop cached models (used by tests and when settings change)."""
    get_chat_model.cache_clear()
