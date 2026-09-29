"""Full stack (HTTP -> pipeline -> real chains -> fake OpenAI server)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

SHORT = "AI tooling adoption grew forty percent across teams this year. " * 8
LONG = "\n\n".join(
    f"Section {i}. " + "Engineers adopted AI tooling and reported faster delivery. " * 40
    for i in range(6)
)


def _schemas(fake):
    return [r["schema"] for r in fake.state.requests]


def test_short_article_end_to_end(fake_llm):
    r = client.post("/api/v1/summarize", json={"article": SHORT, "summary_length": "short"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"] == "How AI Is Reshaping Software Engineering"
    assert body["word_count"] == len(body["summary"].split())
    assert body["metadata"]["chunk_count"] == 1
    assert body["metadata"]["revised"] is False
    # 1 analysis + 1 summary + 1 insights + synthesis + critic + writer
    assert len(fake_llm.state.requests) == 6


def test_long_article_uses_multiple_chunks(fake_llm):
    r = client.post("/api/v1/summarize", json={"article": LONG, "summary_length": "detailed"})
    assert r.status_code == 200, r.text
    n = r.json()["metadata"]["chunk_count"]
    assert n > 1
    s = _schemas(fake_llm)
    assert s.count("ChunkSummary") == n
    assert s.count("ChunkInsights") == n
    assert s.count("ArticleAnalysis") == 1
    assert s.count("DraftSummary") == 1
    assert s.count("CritiqueResult") == 1
    assert s.count("FinalSummary") == 1


def test_stage_order_is_analysis_then_chunks_then_synthesis_critic_writer(fake_llm):
    client.post("/api/v1/summarize", json={"article": LONG})
    s = _schemas(fake_llm)
    assert s[0] == "ArticleAnalysis"
    assert s[-3:] == ["DraftSummary", "CritiqueResult", "FinalSummary"]


def test_revise_verdict_passes_critique_to_writer_once(fake_llm):
    fake_llm.state.critic_status = "REVISE"
    r = client.post("/api/v1/summarize", json={"article": SHORT})
    assert r.status_code == 200
    assert r.json()["metadata"]["revised"] is True
    s = _schemas(fake_llm)
    assert s.count("CritiqueResult") == 1  # no loop back to the critic
    writer_body = [x for x in fake_llm.state.requests if x["schema"] == "FinalSummary"][0]["body"]
    text = " ".join(m["content"] for m in writer_body["messages"] if isinstance(m["content"], str))
    assert "REVISE" in text and "Mention the 40% growth" in text


def test_model_failure_returns_clean_502(fake_llm):
    fake_llm.state.fail_schema = "ArticleAnalysis"
    r = client.post("/api/v1/summarize", json={"article": SHORT})
    assert r.status_code == 502
    assert "temporarily unavailable" in r.json()["detail"]
    assert "boom" not in r.text and "Traceback" not in r.text


def test_single_chain_failure_in_chunks_is_tolerated(fake_llm):
    fake_llm.state.fail_schema = "ChunkInsights"  # every insights call fails
    r = client.post("/api/v1/summarize", json={"article": LONG})
    assert r.status_code == 200, r.text  # summaries still succeed


def test_synthesis_failure_returns_502(fake_llm):
    fake_llm.state.fail_schema = "DraftSummary"
    r = client.post("/api/v1/summarize", json={"article": SHORT})
    assert r.status_code == 502


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"article": ""}, "Please enter an article"),
        ({"article": "too short"}, "too short"),
        ({}, "Please enter an article"),
    ],
)
def test_invalid_input_never_calls_llm(fake_llm, payload, expected):
    r = client.post("/api/v1/summarize", json=payload)
    assert r.status_code == 400
    assert expected in r.json()["detail"]
    assert fake_llm.state.requests == []


def test_article_over_limit_rejected(fake_llm, monkeypatch):
    from app.config.settings import settings

    monkeypatch.setattr(settings, "max_article_chars", 500)
    r = client.post("/api/v1/summarize", json={"article": SHORT * 5})
    assert r.status_code == 400
    assert "too long" in r.json()["detail"]
    assert fake_llm.state.requests == []
