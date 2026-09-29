"""Final writer chain: analysis + draft + critique + length -> FinalSummary."""

from functools import lru_cache

from langchain_core.runnables import Runnable

from app.llm.provider import create_chat_model
from app.prompts.final_writer import LENGTH_GUIDANCE, final_writer_prompt
from app.schemas.analysis import ArticleAnalysis, CritiqueResult, DraftSummary, FinalSummary


@lru_cache(maxsize=1)
def build_final_writer_chain() -> Runnable:
    model = create_chat_model().with_structured_output(FinalSummary)
    return (final_writer_prompt | model).with_config(run_name="final_writer", tags=["final_writer"])


async def run_final_writer(
    analysis: ArticleAnalysis,
    draft: DraftSummary,
    critique: CritiqueResult,
    summary_length: str,
) -> FinalSummary:
    chain = build_final_writer_chain()
    result = await chain.ainvoke(
        {
            "summary_length": summary_length,
            "length_guidance": LENGTH_GUIDANCE.get(summary_length, "250-350 words"),
            "topic": analysis.topic,
            "main_argument": analysis.main_argument,
            "analysis_conclusion": analysis.conclusion,
            "draft_summary": draft.draft_summary,
            "critique_status": critique.status,
            "critique_issues": ", ".join(critique.issues) or "none",
            "critique_missing_points": ", ".join(critique.missing_points) or "none",
            "critique_unsupported_claims": ", ".join(critique.unsupported_claims) or "none",
            "critique_recommendations": ", ".join(critique.recommendations) or "none",
        }
    )
    # word_count should reflect the actual generated summary, not a model guess.
    result.word_count = len(result.summary.split())
    return result
