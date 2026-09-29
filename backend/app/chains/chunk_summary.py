"""Chunk summary chain: one chunk of text -> ChunkSummary."""

from functools import lru_cache

from langchain_core.runnables import Runnable

from app.llm.provider import create_chat_model
from app.prompts.chunk_summary import chunk_summary_prompt
from app.schemas.analysis import ChunkSummary


@lru_cache(maxsize=1)
def build_chunk_summary_chain() -> Runnable:
    """Return a runnable: {"chunk_index": int, "chunk_text": str} -> ChunkSummary."""
    model = create_chat_model().with_structured_output(ChunkSummary)
    return (chunk_summary_prompt | model).with_config(run_name="chunk_summary", tags=["chunk_summary"])


async def run_chunk_summary(chunk_index: int, chunk_text: str) -> ChunkSummary:
    chain = build_chunk_summary_chain()
    result = await chain.ainvoke({"chunk_index": chunk_index, "chunk_text": chunk_text})
    # Guarantee the index matches even if the model returns something odd.
    result.chunk_index = chunk_index
    return result
