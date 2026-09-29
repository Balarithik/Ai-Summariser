"""
Structured outputs produced by the intermediate pipeline stages.

Each of these maps directly to a `.with_structured_output(...)` call in the
corresponding chain, so the LLM is constrained to return exactly this shape.
"""

from typing import List

from pydantic import BaseModel, Field


class ArticleAnalysis(BaseModel):
    """High-level understanding of the whole article."""

    topic: str = Field(description="The overall subject of the article, one sentence.")
    main_argument: str = Field(
        description="The author's central argument or thesis, stated plainly."
    )
    key_points: List[str] = Field(
        default_factory=list, description="The most important points made in the article."
    )
    entities: List[str] = Field(
        default_factory=list,
        description="Important named people, organizations, products, or places mentioned.",
    )
    conclusion: str = Field(
        description="How the article concludes or what it ultimately recommends/implies."
    )


class ChunkSummary(BaseModel):
    """Summary of a single chunk of the article."""

    chunk_index: int = Field(description="0-based index of the chunk this summary covers.")
    summary: str = Field(description="Concise summary of this chunk only.")
    key_points: List[str] = Field(default_factory=list)
    important_facts: List[str] = Field(
        default_factory=list, description="Specific facts, numbers, or figures worth preserving."
    )


class ChunkInsights(BaseModel):
    """Analytical extraction (not a summary) for a single chunk."""

    chunk_index: int = Field(description="0-based index of the chunk these insights cover.")
    claims: List[str] = Field(default_factory=list, description="Assertions the article makes.")
    evidence: List[str] = Field(
        default_factory=list, description="Supporting evidence offered for those claims."
    )
    statistics: List[str] = Field(default_factory=list, description="Numeric data points.")
    cause_effect: List[str] = Field(
        default_factory=list, description="Cause-and-effect relationships described."
    )
    problems: List[str] = Field(default_factory=list, description="Problems the article raises.")
    solutions: List[str] = Field(
        default_factory=list, description="Solutions or responses the article proposes."
    )
    observations: List[str] = Field(
        default_factory=list, description="Other notable analytical observations."
    )


class ChunkResult(BaseModel):
    """Combined result of processing a single chunk (summary + insights)."""

    chunk_index: int
    summary: ChunkSummary | None = None
    insights: ChunkInsights | None = None
    summary_error: str | None = None
    insights_error: str | None = None


class DraftSummary(BaseModel):
    """Synthesis chain output: a coherent, article-level draft."""

    draft_summary: str = Field(description="Coherent article-level draft summary.")
    key_points: List[str] = Field(default_factory=list)
    important_facts: List[str] = Field(default_factory=list)


class CritiqueResult(BaseModel):
    """Critic chain output."""

    status: str = Field(description="Either 'PASS' or 'REVISE'.")
    issues: List[str] = Field(default_factory=list)
    missing_points: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class FinalSummary(BaseModel):
    """Final writer chain output - the shape returned to the API caller."""

    title: str
    summary: str
    key_points: List[str] = Field(default_factory=list)
    main_argument: str
    important_facts: List[str] = Field(default_factory=list)
    conclusion: str
    word_count: int
