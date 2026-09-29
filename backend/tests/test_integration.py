"""
Optional live integration test. Runs ONLY when a real OPENAI_API_KEY is
present in the environment; skipped otherwise so CI needs no paid access.
"""

import os

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_BASE_URL"),
    reason="Set OPENAI_API_KEY (and no OPENAI_BASE_URL override) to run live integration tests.",
)

ARTICLE = (
    "Remote work has changed how companies hire. A 2023 survey of 2,000 managers found "
    "that 62 percent now recruit outside their home city. Supporters argue this widens "
    "the talent pool and lowers office costs. Critics counter that onboarding suffers and "
    "junior employees miss mentorship. Several firms responded with hybrid schedules and "
    "structured buddy programs. The author concludes that companies should treat remote "
    "hiring as a process design problem rather than a perk, investing in onboarding early."
)


def test_live_summarize_short():
    from app.main import app

    r = TestClient(app).post(
        "/api/v1/summarize", json={"article": ARTICLE, "summary_length": "short"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"] and body["summary"]
    assert body["word_count"] == len(body["summary"].split())
