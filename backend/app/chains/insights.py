"""Insight extraction chain: one chunk of text -> ChunkInsights."""

from functools import lru_cache

from langchain_core.runnables import Runnable

from app.llm.provider import get_chunk_model
from app.prompts.insights import insights_prompt
from app.schemas.analysis import ChunkInsights


@lru_cache(maxsize=1)
def build_insights_chain() -> Runnable:
    """Return a runnable: {"chunk_index": int, "chunk_text": str} -> ChunkInsights.

    Uses the lightweight gemini-1.5-flash model so that the heavier
    gemini-3.8-flash quota bucket is reserved for analysis / synthesis / final write.
    """
    model = get_chunk_model().with_structured_output(ChunkInsights)
    return (insights_prompt | model).with_config(run_name="chunk_insights", tags=["chunk_insights"])


async def run_insights(chunk_index: int, chunk_text: str) -> ChunkInsights:
    chain = build_insights_chain()
    result = await chain.ainvoke({"chunk_index": chunk_index, "chunk_text": chunk_text})
    result.chunk_index = chunk_index
    return result
