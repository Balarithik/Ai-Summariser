import pytest

from app.schemas.analysis import (
    ArticleAnalysis,
    ChunkInsights,
    ChunkSummary,
    CritiqueResult,
    DraftSummary,
    FinalSummary,
)
from app.services.pipeline import (
    ArticleSummarizationPipeline,
    InputValidationError,
    validate_article_text,
)


SAMPLE_ARTICLE = " ".join(
    ["This is a reasonably long sample article about testing pipelines."] * 10
)


async def _fake_analysis(article: str) -> ArticleAnalysis:
    return ArticleAnalysis(
        topic="Testing pipelines",
        main_argument="Pipelines should be tested with mocks.",
        key_points=["Mock LLM calls", "Test each stage"],
        entities=["pytest"],
        conclusion="Mocking makes tests fast and reliable.",
    )


async def _fake_chunk_summary(chunk_index: int, chunk_text: str) -> ChunkSummary:
    return ChunkSummary(
        chunk_index=chunk_index,
        summary=f"Summary of chunk {chunk_index}.",
        key_points=["point"],
        important_facts=["fact"],
    )


async def _fake_insights(chunk_index: int, chunk_text: str) -> ChunkInsights:
    return ChunkInsights(
        chunk_index=chunk_index,
        claims=["claim"],
        evidence=["evidence"],
        statistics=[],
        cause_effect=[],
        problems=[],
        solutions=[],
        observations=[],
    )


async def _fake_synthesis(analysis, chunk_results) -> DraftSummary:
    return DraftSummary(
        draft_summary="Draft synthesized summary.",
        key_points=["point"],
        important_facts=["fact"],
    )


async def _fake_critic_pass(article, draft) -> CritiqueResult:
    return CritiqueResult(status="PASS")


async def _fake_critic_revise(article, draft) -> CritiqueResult:
    return CritiqueResult(
        status="REVISE",
        issues=["Missing a key point"],
        recommendations=["Add the missing point"],
    )


async def _fake_final_writer(analysis, draft, critique, summary_length) -> FinalSummary:
    return FinalSummary(
        title="Test Title",
        summary="This is the final generated summary text for the test.",
        key_points=["point"],
        main_argument=analysis.main_argument,
        important_facts=["fact"],
        conclusion=analysis.conclusion,
        word_count=10,
    )


class TestValidation:
    def test_rejects_empty_article(self):
        with pytest.raises(InputValidationError):
            validate_article_text("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(InputValidationError):
            validate_article_text("   ")

    def test_rejects_too_short_article(self):
        with pytest.raises(InputValidationError):
            validate_article_text("Too short.")

    def test_accepts_long_enough_article(self):
        validate_article_text(SAMPLE_ARTICLE)  # should not raise


@pytest.mark.asyncio
async def test_pipeline_runs_end_to_end_with_mocks(monkeypatch):
    monkeypatch.setattr("app.services.pipeline.run_analysis", _fake_analysis)
    monkeypatch.setattr("app.services.pipeline.run_chunk_summary", _fake_chunk_summary)
    monkeypatch.setattr("app.services.pipeline.run_insights", _fake_insights)
    monkeypatch.setattr("app.services.pipeline.run_synthesis", _fake_synthesis)
    monkeypatch.setattr("app.services.pipeline.run_critic", _fake_critic_pass)
    monkeypatch.setattr("app.services.pipeline.run_final_writer", _fake_final_writer)

    pipeline = ArticleSummarizationPipeline(max_concurrency=2)
    result = await pipeline.run(SAMPLE_ARTICLE, "medium")

    assert result.final_summary.title == "Test Title"
    assert result.chunk_count >= 1
    assert result.revised is False


@pytest.mark.asyncio
async def test_pipeline_marks_revised_when_critic_requests_revision(monkeypatch):
    monkeypatch.setattr("app.services.pipeline.run_analysis", _fake_analysis)
    monkeypatch.setattr("app.services.pipeline.run_chunk_summary", _fake_chunk_summary)
    monkeypatch.setattr("app.services.pipeline.run_insights", _fake_insights)
    monkeypatch.setattr("app.services.pipeline.run_synthesis", _fake_synthesis)
    monkeypatch.setattr("app.services.pipeline.run_critic", _fake_critic_revise)
    monkeypatch.setattr("app.services.pipeline.run_final_writer", _fake_final_writer)

    pipeline = ArticleSummarizationPipeline(max_concurrency=2)
    result = await pipeline.run(SAMPLE_ARTICLE, "short")

    assert result.revised is True


@pytest.mark.asyncio
async def test_pipeline_rejects_invalid_input_before_calling_llm(monkeypatch):
    async def _boom(*args, **kwargs):
        raise AssertionError("LLM chain should not be called for invalid input")

    monkeypatch.setattr("app.services.pipeline.run_analysis", _boom)

    pipeline = ArticleSummarizationPipeline()
    with pytest.raises(InputValidationError):
        await pipeline.run("too short", "medium")


@pytest.mark.asyncio
async def test_pipeline_handles_single_chunk_failure_gracefully(monkeypatch):
    call_count = {"n": 0}

    async def _flaky_summary(chunk_index, chunk_text):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated transient failure")
        return await _fake_chunk_summary(chunk_index, chunk_text)

    monkeypatch.setattr("app.services.pipeline.run_analysis", _fake_analysis)
    monkeypatch.setattr("app.services.pipeline.run_chunk_summary", _flaky_summary)
    monkeypatch.setattr("app.services.pipeline.run_insights", _fake_insights)
    monkeypatch.setattr("app.services.pipeline.run_synthesis", _fake_synthesis)
    monkeypatch.setattr("app.services.pipeline.run_critic", _fake_critic_pass)
    monkeypatch.setattr("app.services.pipeline.run_final_writer", _fake_final_writer)

    # Long article -> multiple chunks -> first chunk summary fails, pipeline
    # should still complete using the remaining data.
    long_article = " ".join(["Sentence about pipelines and testing."] * 800)
    pipeline = ArticleSummarizationPipeline(max_concurrency=2)
    result = await pipeline.run(long_article, "medium")

    assert result.final_summary.title == "Test Title"


LONG_ARTICLE = "\n\n".join(
    f"Paragraph {i}. " + "Pipelines need careful testing and observability. " * 40 for i in range(12)
)


@pytest.mark.asyncio
async def test_long_article_is_split_into_multiple_chunks(monkeypatch):
    monkeypatch.setattr("app.services.pipeline.run_analysis", _fake_analysis)
    monkeypatch.setattr("app.services.pipeline.run_chunk_summary", _fake_chunk_summary)
    monkeypatch.setattr("app.services.pipeline.run_insights", _fake_insights)
    monkeypatch.setattr("app.services.pipeline.run_synthesis", _fake_synthesis)
    monkeypatch.setattr("app.services.pipeline.run_critic", _fake_critic_pass)
    monkeypatch.setattr("app.services.pipeline.run_final_writer", _fake_final_writer)

    result = await ArticleSummarizationPipeline(max_concurrency=3).run(LONG_ARTICLE, "medium")
    assert result.chunk_count > 1


@pytest.mark.asyncio
async def test_chunk_results_reach_synthesis_in_order_even_if_finished_out_of_order(monkeypatch):
    import asyncio

    async def slow_early_chunks(chunk_index, chunk_text):
        await asyncio.sleep(0.05 if chunk_index == 0 else 0)  # chunk 0 finishes last
        return await _fake_chunk_summary(chunk_index, chunk_text)

    seen = {}

    async def capture_synthesis(analysis, chunk_results):
        seen["order"] = [c.chunk_index for c in chunk_results]
        return await _fake_synthesis(analysis, chunk_results)

    monkeypatch.setattr("app.services.pipeline.run_analysis", _fake_analysis)
    monkeypatch.setattr("app.services.pipeline.run_chunk_summary", slow_early_chunks)
    monkeypatch.setattr("app.services.pipeline.run_insights", _fake_insights)
    monkeypatch.setattr("app.services.pipeline.run_synthesis", capture_synthesis)
    monkeypatch.setattr("app.services.pipeline.run_critic", _fake_critic_pass)
    monkeypatch.setattr("app.services.pipeline.run_final_writer", _fake_final_writer)

    await ArticleSummarizationPipeline(max_concurrency=8).run(LONG_ARTICLE, "medium")
    assert seen["order"] == sorted(seen["order"]) and len(seen["order"]) > 2


@pytest.mark.asyncio
async def test_concurrency_never_exceeds_limit(monkeypatch):
    import asyncio

    state = {"in_flight": 0, "peak": 0}

    async def tracked_summary(chunk_index, chunk_text):
        state["in_flight"] += 1
        state["peak"] = max(state["peak"], state["in_flight"])
        await asyncio.sleep(0.02)
        state["in_flight"] -= 1
        return await _fake_chunk_summary(chunk_index, chunk_text)

    monkeypatch.setattr("app.services.pipeline.run_analysis", _fake_analysis)
    monkeypatch.setattr("app.services.pipeline.run_chunk_summary", tracked_summary)
    monkeypatch.setattr("app.services.pipeline.run_insights", _fake_insights)
    monkeypatch.setattr("app.services.pipeline.run_synthesis", _fake_synthesis)
    monkeypatch.setattr("app.services.pipeline.run_critic", _fake_critic_pass)
    monkeypatch.setattr("app.services.pipeline.run_final_writer", _fake_final_writer)

    result = await ArticleSummarizationPipeline(max_concurrency=2).run(LONG_ARTICLE, "medium")
    assert result.chunk_count > 2
    assert state["peak"] <= 2


@pytest.mark.asyncio
async def test_all_chunks_failing_raises(monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr("app.services.pipeline.run_analysis", _fake_analysis)
    monkeypatch.setattr("app.services.pipeline.run_chunk_summary", boom)
    monkeypatch.setattr("app.services.pipeline.run_insights", boom)

    with pytest.raises(RuntimeError):
        await ArticleSummarizationPipeline().run(SAMPLE_ARTICLE, "medium")


@pytest.mark.asyncio
async def test_rejects_article_over_max_length(monkeypatch):
    from app.config.settings import settings

    monkeypatch.setattr(settings, "max_article_chars", 100)
    with pytest.raises(InputValidationError):
        await ArticleSummarizationPipeline().run(SAMPLE_ARTICLE, "medium")
