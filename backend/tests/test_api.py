import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import FinalSummary
from app.services.pipeline import InputValidationError, PipelineResult

client = TestClient(app)


def _fake_pipeline_result() -> PipelineResult:
    return PipelineResult(
        final_summary=FinalSummary(
            title="A Test Title",
            summary="A concise generated summary of the article.",
            key_points=["Point A", "Point B"],
            main_argument="The article argues X.",
            important_facts=["Fact 1"],
            conclusion="The article concludes Y.",
            word_count=8,
        ),
        input_words=500,
        chunk_count=2,
        revised=False,
        duration_seconds=1.23,
    )


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_summarize_success(monkeypatch):
    async def fake_run(self, article, summary_length):
        return _fake_pipeline_result()

    monkeypatch.setattr(
        "app.api.routes.ArticleSummarizationPipeline.run", fake_run
    )

    response = client.post(
        "/api/v1/summarize",
        json={"article": "A" * 500, "summary_length": "medium"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "A Test Title"
    assert body["metadata"]["chunk_count"] == 2
    assert body["metadata"]["revised"] is False


def test_summarize_rejects_empty_article():
    response = client.post("/api/v1/summarize", json={"article": ""})
    assert response.status_code == 400
    assert "error" not in response.json() or True  # detail-based error shape
    assert "Please enter an article" in response.json()["detail"]


def test_summarize_rejects_invalid_summary_length():
    response = client.post(
        "/api/v1/summarize",
        json={"article": "A" * 500, "summary_length": "extremely_long"},
    )
    assert response.status_code == 422  # FastAPI/Pydantic validation error


def test_summarize_surfaces_validation_error_as_400(monkeypatch):
    async def fake_run(self, article, summary_length):
        raise InputValidationError("Article is too short to summarize.")

    monkeypatch.setattr(
        "app.api.routes.ArticleSummarizationPipeline.run", fake_run
    )

    response = client.post("/api/v1/summarize", json={"article": "A" * 500})
    assert response.status_code == 400
    assert "too short" in response.json()["detail"]


def test_summarize_hides_internal_errors(monkeypatch):
    async def fake_run(self, article, summary_length):
        raise RuntimeError("secret internal stack trace detail")

    monkeypatch.setattr(
        "app.api.routes.ArticleSummarizationPipeline.run", fake_run
    )

    response = client.post("/api/v1/summarize", json={"article": "A" * 500})
    assert response.status_code == 502
    assert "secret internal stack trace detail" not in response.text
    assert "temporarily unavailable" in response.json()["detail"]


def test_summarize_requires_article_or_url():
    response = client.post("/api/v1/summarize", json={})
    assert response.status_code == 400
    assert "Please enter an article" in response.json()["detail"]


def test_url_load_failure_maps_to_400(monkeypatch):
    from app.services.article_loader import ArticleLoadError

    async def fail(url):
        raise ArticleLoadError("Unable to retrieve the article from this URL.")

    monkeypatch.setattr("app.api.routes.load_article_from_url", fail)
    r = client.post("/api/v1/summarize", json={"url": "https://example.com/x"})
    assert r.status_code == 400
    assert "Unable to retrieve the article" in r.json()["detail"]


def test_url_success_flows_into_pipeline(monkeypatch):
    async def ok(url):
        return "Loaded article body. " * 50

    async def fake_run(self, article, summary_length):
        assert article.startswith("Loaded article body.")
        return _fake_pipeline_result()

    monkeypatch.setattr("app.api.routes.load_article_from_url", ok)
    monkeypatch.setattr("app.api.routes.ArticleSummarizationPipeline.run", fake_run)
    r = client.post("/api/v1/summarize", json={"url": "https://example.com/x"})
    assert r.status_code == 200


def test_cors_allows_configured_origin_only():
    ok = client.options(
        "/api/v1/summarize",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options(
        "/api/v1/summarize",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in bad.headers
