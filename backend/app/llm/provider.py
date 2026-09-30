"""
Dedicated LLM provider module.

This is the ONLY place in the application that instantiates a chat model.
Instances are cached per temperature, so the rest of the app never builds
the model repeatedly. The active provider is chosen with LLM_PROVIDER
("openai" or "gemini"); adding another provider means changing this file only.
"""

import asyncio
import logging
import time
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.rate_limiters import InMemoryRateLimiter

from app.config.settings import settings
from app.llm.errors import ProviderError, ProviderRateLimitError, ProviderConfigurationError, classify_exception

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


# ---------------------------------------------------------------------------
# Model stratification: different models for different workloads so that
# quota is distributed across buckets rather than concentrated on one model.
# ---------------------------------------------------------------------------
_CHUNK_MODEL: Optional[BaseChatModel] = None
_FLASH_MODEL: Optional[BaseChatModel] = None


def get_chunk_model(temperature: Optional[float] = None, rate_limiter: Optional[InMemoryRateLimiter] = None) -> BaseChatModel:
    """Return a model for per-chunk operations (summary + insights).

    We use a cheaper/faster model for the many per-chunk calls so that the
    more expensive gemini-3.1-flash-lite is reserved for analysis, synthesis, and
    the final writer — each model has its own quota bucket.

    Defaults: temperature from settings, rate_limiter from process-wide throttle.
    The model name is read from settings.gemini_model (configured via .env)
    so that it stays compatible with your Gemini API version.
    """

    from langchain_google_genai import ChatGoogleGenerativeAI

    if temperature is None:
        temperature = settings.temperature
    if rate_limiter is None:
        rate_limiter = get_llm_rate_limiter()

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=temperature,
        google_api_key=settings.google_api_key,
        timeout=settings.llm_request_timeout,
        max_retries=settings.llm_max_retries,
        rate_limiter=rate_limiter,
    )


def _get_flash_model(temperature: float, rate_limiter) -> BaseChatModel:
    """Return the configured gemini-3.8-flash model for heavyweight stages."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=temperature,
        google_api_key=settings.google_api_key,
        timeout=settings.llm_request_timeout,
        max_retries=settings.llm_max_retries,
        rate_limiter=rate_limiter,
    )


def _extract_retry_delay(exc: Exception) -> Optional[float]:
    """Try to extract Google's retry_delay (seconds) from a rate-limit exception."""
    exc_str = str(exc).lower()
    # Google sometimes includes retry_delay in the message or as an attribute.
    import re
    m = re.search(r"retry_delay[=:]\s*([0-9.]+)", exc_str)
    if m:
        return float(m.group(1))
    # Also check for a numeric seconds hint like "try again in 9s"
    m2 = re.search(r"in\s+([0-9.]+)\s*s", exc_str)
    if m2:
        return float(m2.group(1))
    return None


def _rate_limited_gemini_call(
    func, max_retries: int = settings.llm_max_retries, backoff_base: float = 2.0
):
    """Decorator/ wrapper that respects Gemini's retry_delay and adds exponential backoff."""

    async def wrapper(*args, **kwargs):
        last_err: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - broad, we classify below
                last_err = exc
                classified = classify_exception(exc)

                # If it's a rate limit error, try to respect retry_delay
                if isinstance(classified, ProviderRateLimitError):
                    delay = _extract_retry_delay(exc)
                    if delay is not None and delay > 0:
                        logger.info(
                            "Gemini rate limit hit, respecting retry_delay=%.1fs (attempt %d/%d)",
                            delay,
                            attempt,
                            max_retries,
                        )
                        await asyncio.sleep(delay)
                        # Still try once more after the delay
                        try:
                            return await func(*args, **kwargs)
                        except Exception as e:
                            last_err = e
                            classified = classify_exception(e)
                            # fall through to exponential backoff below
                # Exponential backoff: backoff_base ** (attempt - 1) seconds
                # Cap at 30 seconds; also add jitter.
                wait = min(backoff_base ** (attempt - 1), 30)
                jitter = wait * 0.1 * (attempt % 10)  # tiny jitter
                logger.warning(
                    "Gemini call attempt %d/%d failed: %s. Backing off %.1fs",
                    attempt,
                    max_retries,
                    classified.message,
                    wait + jitter,
                )
                await asyncio.sleep(wait + jitter)
                continue

        # Exhausted retries
        raise last_err  # type: ignore[return-value]

    return wrapper


def _build_openai(temperature: float, rate_limiter) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    if not settings.openai_api_key:
        raise ProviderConfigurationError(
            "OPENAI_API_KEY is not set. LLM calls will fail until it is configured."
        )

    kwargs = {}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url

    return ChatOpenAI(
        model=settings.openai_model,
        temperature=temperature,
        api_key=settings.openai_api_key,
        timeout=settings.llm_request_timeout,
        max_retries=settings.llm_max_retries,
        rate_limiter=rate_limiter,
        **kwargs,
    )


def get_chat_model(temperature: Optional[float] = None) -> BaseChatModel:
    """Return a cached chat model for the configured provider and temperature."""
    temp = settings.temperature if temperature is None else temperature
    limiter = get_llm_rate_limiter()

    if settings.llm_provider == "gemini":
        # Return the heavyweight model; per-chunk chains will use get_chunk_model()
        return _get_flash_model(temp, limiter)
    return _build_openai(temp, limiter)


def create_chat_model(temperature: Optional[float] = None) -> BaseChatModel:
    """Backward-compatible alias for get_chat_model."""
    return get_chat_model(temperature)


def clear_model_cache() -> None:
    """Drop cached models and the shared throttle (tests / settings changes)."""
    global _rate_limiter, _CHUNK_MODEL, _FLASH_MODEL
    _rate_limiter = None
    _CHUNK_MODEL = None
    _FLASH_MODEL = None
    get_chat_model.cache_clear()
