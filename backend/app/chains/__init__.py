"""LangChain chain definitions, one module per pipeline stage."""

from app.chains.analysis import build_analysis_chain
from app.chains.chunk_summary import build_chunk_summary_chain
from app.chains.critic import build_critic_chain
from app.chains.final_writer import build_final_writer_chain
from app.chains.insights import build_insights_chain
from app.chains.synthesis import build_synthesis_chain
from app.llm.provider import clear_model_cache


def clear_chain_caches() -> None:
    """Reset cached chains and models (tests / settings changes)."""
    for builder in (
        build_analysis_chain,
        build_chunk_summary_chain,
        build_insights_chain,
        build_synthesis_chain,
        build_critic_chain,
        build_final_writer_chain,
    ):
        builder.cache_clear()
    clear_model_cache()
