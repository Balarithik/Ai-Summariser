import pytest

from app.config.settings import settings
from app.llm.provider import clear_model_cache, get_chat_model


@pytest.fixture(autouse=True)
def _clean_cache():
    clear_model_cache()
    yield
    clear_model_cache()


def test_default_provider_is_openai(monkeypatch):
    from langchain_openai import ChatOpenAI

    monkeypatch.setattr(settings, "llm_provider", "openai")
    assert isinstance(get_chat_model(), ChatOpenAI)


def test_gemini_provider_selected(monkeypatch):
    pytest.importorskip("langchain_google_genai")
    from langchain_google_genai import ChatGoogleGenerativeAI

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "google_api_key", "test-key")
    model = get_chat_model()
    assert isinstance(model, ChatGoogleGenerativeAI)
    assert get_chat_model() is model  # still cached


def test_outbound_rate_limiter_attached_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_requests_per_second", 2.0)
    assert get_chat_model().rate_limiter is not None


def test_no_outbound_limiter_by_default(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_requests_per_second", 0.0)
    assert get_chat_model().rate_limiter is None
