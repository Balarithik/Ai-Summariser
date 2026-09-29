"""
Dedicated LLM provider module.

This is the ONLY place in the application that instantiates a chat model.
Instances are cached per temperature, so the rest of the app never builds
the model repeatedly. The active provider is chosen with LLM_PROVIDER
("openai" or "gemini"); adding another provider means changing this file only.
"""

import logging
from functools import lru_cache
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.rate_limiters import InMemoryRateLimiter

from app.config.settings import settings

logger = logging.getLogger(__name__)

_rate_limiter: Optional[InMemoryRateLimiter] = None


def get_llm_rate_limiter() -> Optional[InMemoryRateLimiter]:
    """
    Process-wide outbound throttle shared by every chat model instance, so
    parallel chunk calls collectively stay under the provider's quota.
    Returns None when LLM_REQUESTS_PER_SECOND is 0 (unlimited).
    """
    global _rate_limiter
    rps = settings.llm_requests_per_second
    if rps <= 0:
        return None
    if _rate_limiter is None:
        _rate_limiter = InMemoryRateLimiter(
            requests_per_second=rps,
            check_every_n_seconds=0.05,
            max_bucket_size=max(1, int(rps)),
        )
    return _rate_limiter


def _build_openai(temperature: float, rate_limiter) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is not set. LLM calls will fail until it is configured.")

    kwargs = {}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url

    return ChatOpenAI(
        model=settings.openai_model,
        temperature=temperature,
        # A placeholder keeps client construction from failing; real calls
        # without a key are rejected by the API and surface as a 502.
        api_key=settings.openai_api_key or "missing-api-key",
        timeout=settings.llm_request_timeout,
        max_retries=settings.llm_max_retries,
        rate_limiter=rate_limiter,
        **kwargs,
    )


def _build_gemini(temperature: float, rate_limiter) -> BaseChatModel:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:  # pragma: no cover - depends on install
        raise RuntimeError(
            "LLM_PROVIDER=gemini requires the 'langchain-google-genai' package "
            "(pip install langchain-google-genai)."
        ) from exc

    if not settings.google_api_key:
        logger.warning("GOOGLE_API_KEY is not set. LLM calls will fail until it is configured.")

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=temperature,
        google_api_key=settings.google_api_key or "missing-api-key",
        timeout=settings.llm_request_timeout,
        max_retries=settings.llm_max_retries,
        rate_limiter=rate_limiter,
    )


@lru_cache(maxsize=8)
def get_chat_model(temperature: Optional[float] = None) -> BaseChatModel:
    """Return a cached chat model for the configured provider and temperature."""
    temp = settings.temperature if temperature is None else temperature
    limiter = get_llm_rate_limiter()

    if settings.llm_provider == "gemini":
        return _build_gemini(temp, limiter)
    return _build_openai(temp, limiter)


def create_chat_model(temperature: Optional[float] = None) -> BaseChatModel:
    """Backward-compatible alias for get_chat_model."""
    return get_chat_model(temperature)


def clear_model_cache() -> None:
    """Drop cached models and the shared throttle (tests / settings changes)."""
    global _rate_limiter
    _rate_limiter = None
    get_chat_model.cache_clear()
