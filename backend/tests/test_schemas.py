import pytest
from pydantic import ValidationError

from app.schemas.analysis import ArticleAnalysis, CritiqueResult, FinalSummary
from app.schemas.article import SummarizeRequest, SummaryLength


def test_summarize_request_defaults_to_medium():
    req = SummarizeRequest(article="Some article text.")
    assert req.summary_length == SummaryLength.MEDIUM


def test_summarize_request_rejects_invalid_length():
    with pytest.raises(ValidationError):
        SummarizeRequest(article="Some article text.", summary_length="extra_long")


def test_summarize_request_strips_whitespace():
    req = SummarizeRequest(article="   padded text   ")
    assert req.article == "padded text"


def test_summarize_request_allows_url_only():
    req = SummarizeRequest(url="https://example.com/article")
    assert req.article is None
    assert req.url == "https://example.com/article"


def test_article_analysis_requires_core_fields():
    with pytest.raises(ValidationError):
        ArticleAnalysis(topic="AI")  # missing main_argument / conclusion


def test_article_analysis_defaults_lists():
    analysis = ArticleAnalysis(
        topic="AI in software",
        main_argument="AI changes how software is built.",
        conclusion="Adopt AI carefully.",
    )
    assert analysis.key_points == []
    assert analysis.entities == []


def test_critique_result_defaults():
    critique = CritiqueResult(status="PASS")
    assert critique.issues == []
    assert critique.recommendations == []


def test_final_summary_shape():
    summary = FinalSummary(
        title="Title",
        summary="Summary text.",
        main_argument="Main argument.",
        conclusion="Conclusion.",
        word_count=2,
    )
    assert summary.key_points == []
    assert summary.word_count == 2
