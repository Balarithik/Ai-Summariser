"""Tests for provider error classification."""

import pytest

from app.llm.errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderError,
    ProviderQuotaExhaustedError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    classify_exception,
)


class TestClassifyException:
    def test_quota_exhausted_openai(self):
        exc = Exception("Error code: 429 - insufficient_quota: credit_balance_exhausted")
        result = classify_exception(exc)
        assert isinstance(result, ProviderQuotaExhaustedError)
        assert not result.retryable

    def test_quota_exhausted_message(self):
        exc = Exception("You have no credits remaining. Add credits to continue using the API")
        result = classify_exception(exc)
        assert isinstance(result, ProviderQuotaExhaustedError)

    def test_authentication_error(self):
        exc = Exception("Error code: 401 - invalid_api_key")
        result = classify_exception(exc)
        assert isinstance(result, ProviderAuthenticationError)
        assert not result.retryable

    def test_rate_limit_error(self):
        exc = Exception("Error code: 429 - rate_limit_exceeded")
        result = classify_exception(exc)
        assert isinstance(result, ProviderRateLimitError)
        assert result.retryable

    def test_timeout_error(self):
        exc = Exception("Request timed out after 60 seconds")
        result = classify_exception(exc)
        assert isinstance(result, ProviderTimeoutError)
        assert result.retryable

    def test_server_error(self):
        exc = Exception("Error code: 500 - server_error")
        result = classify_exception(exc)
        assert isinstance(result, ProviderUnavailableError)
        assert result.retryable

    def test_unknown_error(self):
        exc = Exception("Something completely unexpected happened")
        result = classify_exception(exc)
        assert isinstance(result, ProviderUnavailableError)

    def test_quota_not_retryable(self):
        exc = Exception("credit_balance_exhausted")
        result = classify_exception(exc)
        assert not result.retryable

    def test_rate_limit_is_retryable(self):
        exc = Exception("rate_limit_exceeded")
        result = classify_exception(exc)
        assert result.retryable


class TestProviderErrorClasses:
    def test_configuration_error_not_retryable(self):
        err = ProviderConfigurationError("missing key")
        assert not err.retryable
        assert "missing key" in err.message

    def test_quota_error_message(self):
        err = ProviderQuotaExhaustedError()
        assert "quota" in err.message.lower() or "credits" in err.message.lower()

    def test_authentication_error_message(self):
        err = ProviderAuthenticationError()
        assert "api key" in err.message.lower() or "authentication" in err.message.lower()
