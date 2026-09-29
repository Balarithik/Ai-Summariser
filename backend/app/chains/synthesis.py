"""Synthesis chain: analysis + all chunk results -> DraftSummary."""

from typing import List

from functools import lru_cache

from langchain_core.runnables import Runnable

from app.llm.provider import create_chat_model
from app.prompts.synthesis import synthesis_prompt
from app.schemas.analysis import ArticleAnalysis, ChunkResult, DraftSummary


@lru_cache(maxsize=1)
def build_synthesis_chain() -> Runnable:
    model = create_chat_model().with_structured_output(DraftSummary)
    return (synthesis_prompt | model).with_config(run_name="synthesis", tags=["synthesis"])


def _format_chunk_summaries(chunk_results: List[ChunkResult]) -> str:
    lines = []
    for cr in sorted(chunk_results, key=lambda c: c.chunk_index):
        if cr.summary is not None:
            lines.append(
                f"[Chunk {cr.chunk_index}] {cr.summary.summary} "
                f"(key points: {', '.join(cr.summary.key_points) or 'none'}; "
                f"facts: {', '.join(cr.summary.important_facts) or 'none'})"
            )
        elif cr.summary_error:
            lines.append(f"[Chunk {cr.chunk_index}] (summary unavailable: {cr.summary_error})")
    return "\n".join(lines) if lines else "None available."


def _format_chunk_insights(chunk_results: List[ChunkResult]) -> str:
    lines = []
    for cr in sorted(chunk_results, key=lambda c: c.chunk_index):
        if cr.insights is not None:
            ins = cr.insights
            lines.append(
                f"[Chunk {cr.chunk_index}] claims: {', '.join(ins.claims) or 'none'}; "
                f"evidence: {', '.join(ins.evidence) or 'none'}; "
                f"statistics: {', '.join(ins.statistics) or 'none'}; "
                f"cause_effect: {', '.join(ins.cause_effect) or 'none'}; "
                f"problems: {', '.join(ins.problems) or 'none'}; "
                f"solutions: {', '.join(ins.solutions) or 'none'}; "
                f"observations: {', '.join(ins.observations) or 'none'}"
            )
        elif cr.insights_error:
            lines.append(f"[Chunk {cr.chunk_index}] (insights unavailable: {cr.insights_error})")
    return "\n".join(lines) if lines else "None available."


async def run_synthesis(
    analysis: ArticleAnalysis, chunk_results: List[ChunkResult]
) -> DraftSummary:
    chain = build_synthesis_chain()
    result = await chain.ainvoke(
        {
            "topic": analysis.topic,
            "main_argument": analysis.main_argument,
            "analysis_key_points": ", ".join(analysis.key_points) or "none",
            "analysis_conclusion": analysis.conclusion,
            "chunk_summaries": _format_chunk_summaries(chunk_results),
            "chunk_insights": _format_chunk_insights(chunk_results),
        }
    )
    return result
