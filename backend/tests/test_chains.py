"""Run the REAL chains (prompt -> ChatOpenAI -> structured parse) against a fake server."""

from app.chains.analysis import run_analysis
from app.chains.chunk_summary import run_chunk_summary
from app.chains.critic import run_critic
from app.chains.final_writer import run_final_writer
from app.chains.insights import run_insights
from app.chains.synthesis import run_synthesis
from app.schemas.analysis import ChunkResult

ARTICLE = "AI tooling adoption grew 40 percent. " * 30


async def test_all_chains_produce_typed_output(fake_llm):
    analysis = await run_analysis(ARTICLE)
    assert analysis.topic

    summary = await run_chunk_summary(3, ARTICLE)
    assert summary.chunk_index == 3  # index is enforced by the chain, not the model

    insights = await run_insights(5, ARTICLE)
    assert insights.chunk_index == 5 and insights.claims

    results = [ChunkResult(chunk_index=3, summary=summary, insights=insights)]
    draft = await run_synthesis(analysis, results)
    assert draft.draft_summary

    critique = await run_critic(ARTICLE, draft)
    assert critique.status == "PASS"

    final = await run_final_writer(analysis, draft, critique, "medium")
    assert final.title
    assert final.word_count == len(final.summary.split())  # recomputed, not trusted


async def test_each_chain_requests_its_own_schema(fake_llm):
    analysis = await run_analysis(ARTICLE)
    await run_chunk_summary(0, ARTICLE)
    await run_insights(0, ARTICLE)
    schemas = [r["schema"] for r in fake_llm.state.requests]
    assert schemas == ["ArticleAnalysis", "ChunkSummary", "ChunkInsights"]
    assert analysis is not None


async def test_prompts_receive_variables(fake_llm):
    await run_chunk_summary(2, "UNIQUE-CHUNK-MARKER text")
    body = fake_llm.state.requests[-1]["body"]
    text = " ".join(m["content"] for m in body["messages"] if isinstance(m["content"], str))
    assert "UNIQUE-CHUNK-MARKER" in text
    assert "chunk 2" in text


async def test_llm_is_instantiated_once_per_temperature(fake_llm):
    from app.llm.provider import get_chat_model

    assert get_chat_model() is get_chat_model()
    assert get_chat_model(0) is get_chat_model(0)
