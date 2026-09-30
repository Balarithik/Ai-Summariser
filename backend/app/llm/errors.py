"""
Provider error classification.

Maps provider-specific exceptions to application-level error types so the API
can return meaningful, safe error messages without leaking internals.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Base class for all provider-related errors."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable


class ProviderConfigurationError(ProviderError):
    """Raised when the provider is misconfigured (missing key, invalid model, etc.)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=False)


class ProviderAuthenticationError(ProviderError):
    """Raised when the provider rejects the API key."""

    def __init__(self, message: str = "The AI provider rejected the API key.") -> None:
        super().__init__(message, retryable=False)


class ProviderQuotaExhaustedError(ProviderError):
    """Raised when the provider account has no credits/quota remaining."""

    def __init__(
        self, message: str = "The configured AI provider has exhausted its API quota. Please switch providers or add credits."
    ) -> None:
        super().__init__(message, retryable=False)


class ProviderRateLimitError(ProviderError):
    """Raised when the provider rate-limits the request (transient)."""

    def __init__(self, message: str = "The AI provider is rate-limiting requests. Please try again later.") -> None:
        super().__init__(message, retryable=True)


class ProviderTimeoutError(ProviderError):
    """Raised when the provider request times out."""

    def __init__(self, message: str = "The AI provider request timed out. Please try again.") -> None:
        super().__init__(message, retryable=True)


class ProviderUnavailableError(ProviderError):
    """Raised when the provider is temporarily unavailable."""

    def __init__(self, message: str = "The AI service is temporarily unavailable. Please try again.") -> None:
        super().__init__(message, retryable=True)


def classify_exception(exc: Exception) -> ProviderError:
    """
    Classify a provider exception into a typed ProviderError.

    This function inspects the exception type and message to determine the
    appropriate error category. It never raises - if classification fails,
    it returns a generic ProviderError.
    """
    exc_str = str(exc).lower()
    exc_type = type(exc).__name__.lower()

    # Check for quota/credit exhaustion - these should NOT be retried
    quota_indicators = [
        "insufficient_quota",
        "credit_balance_exhausted",
        "quota_exceeded",
        "no credits remaining",
        "billing_hard_limit",
        "exceeded your current quota",
    ]
    if any(indicator in exc_str for indicator in quota_indicators):
        logger.warning("Provider quota exhausted: %s", exc)
        return ProviderQuotaExhaustedError()

    # Check for authentication errors
    auth_indicators = [
        "invalid_api_key",
        "incorrect api key",
        "authentication",
        "unauthorized",
        "401",
        "api key not valid",
    ]
    if any(indicator in exc_str for indicator in auth_indicators):
        logger.warning("Provider authentication failed: %s", exc)
        return ProviderAuthenticationError()

    # Check for rate limiting (transient)
    rate_limit_indicators = [
        "rate_limit",
        "ratelimit",
        "too many requests",
        "429",
        "quota exceeded for requests",
        "request rate",
    ]
    if any(indicator in exc_str for indicator in rate_limit_indicators):
        logger.warning("Provider rate limit hit: %s", exc)
        return ProviderRateLimitError()

    # Check for timeout
    timeout_indicators = [
        "timeout",
        "timed out",
        "deadline exceeded",
    ]
    if any(indicator in exc_str for indicator in timeout_indicators):
        logger.warning("Provider request timed out: %s", exc)
        return ProviderTimeoutError()

    # Check for server errors (transient)
    server_error_indicators = [
        "500",
        "502",
        "503",
        "server_error",
        "service unavailable",
        "internal error",
    ]
    if any(indicator in exc_str for indicator in server_error_indicators):
        logger.warning("Provider server error: %s", exc)
        return ProviderUnavailableError()

    # Default: generic provider error
    logger.warning("Unclassified provider error: %s", exc)
    return ProviderUnavailableError()
