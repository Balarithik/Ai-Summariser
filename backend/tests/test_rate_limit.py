from fastapi.testclient import TestClient

from app.api.rate_limit import SlidingWindowRateLimiter
from app.config.settings import settings
from app.main import app
from app.schemas.analysis import FinalSummary
from app.services.pipeline import PipelineResult

client = TestClient(app)


def _result() -> PipelineResult:
    return PipelineResult(
        final_summary=FinalSummary(
            title="T", summary="S", key_points=[], main_argument="M",
            important_facts=[], conclusion="C", word_count=1,
        ),
        input_words=100, chunk_count=1, revised=False, duration_seconds=0.1,
    )


def test_limiter_allows_up_to_limit_then_blocks():
    rl = SlidingWindowRateLimiter()
    assert rl.check("a", 2, 60) == 0.0
    assert rl.check("a", 2, 60) == 0.0
    assert rl.check("a", 2, 60) > 0.0


def test_limiter_is_per_client():
    rl = SlidingWindowRateLimiter()
    assert rl.check("a", 1, 60) == 0.0
    assert rl.check("b", 1, 60) == 0.0
    assert rl.check("a", 1, 60) > 0.0


def test_limiter_window_expires(monkeypatch):
    import app.api.rate_limit as mod

    now = [1000.0]
    monkeypatch.setattr(mod.time, "monotonic", lambda: now[0])
    rl = SlidingWindowRateLimiter()
    assert rl.check("a", 1, 10) == 0.0
    assert rl.check("a", 1, 10) > 0.0
    now[0] += 11
    assert rl.check("a", 1, 10) == 0.0


def test_endpoint_returns_429_with_retry_after(monkeypatch):
    async def fake_run(self, article, summary_length):
        return _result()

    monkeypatch.setattr("app.api.routes.ArticleSummarizationPipeline.run", fake_run)
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_requests", 2)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)

    body = {"article": "A" * 500}
    assert client.post("/api/v1/summarize", json=body).status_code == 200
    assert client.post("/api/v1/summarize", json=body).status_code == 200
    r = client.post("/api/v1/summarize", json=body)
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1
    assert "Too many requests" in r.json()["detail"]


def test_health_is_not_rate_limited(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_requests", 1)
    for _ in range(5):
        assert client.get("/api/v1/health").status_code == 200
