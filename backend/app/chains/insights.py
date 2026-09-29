"""Insight extraction chain: one chunk of text -> ChunkInsights."""

from functools import lru_cache

from langchain_core.runnables import Runnable

from app.llm.provider import create_chat_model
from app.prompts.insights import insights_prompt
from app.schemas.analysis import ChunkInsights


@lru_cache(maxsize=1)
def build_insights_chain() -> Runnable:
    """Return a runnable: {"chunk_index": int, "chunk_text": str} -> ChunkInsights."""
    model = create_chat_model().with_structured_output(ChunkInsights)
    return (insights_prompt | model).with_config(run_name="chunk_insights", tags=["chunk_insights"])


async def run_insights(chunk_index: int, chunk_text: str) -> ChunkInsights:
    chain = build_insights_chain()
    result = await chain.ainvoke({"chunk_index": chunk_index, "chunk_text": chunk_text})
    result.chunk_index = chunk_index
    return result
