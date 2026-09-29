"""Response-side schemas: what the API returns to the client."""

from typing import List

from pydantic import BaseModel, Field


class ResultMetadata(BaseModel):
    input_words: int
    chunk_count: int
    revised: bool = Field(
        default=False, description="Whether the critic requested a revision cycle."
    )
    duration_seconds: float


class SummarizeResponse(BaseModel):
    """Body of the successful POST /api/v1/summarize response."""

    title: str
    summary: str
    key_points: List[str]
    main_argument: str
    important_facts: List[str]
    conclusion: str
    word_count: int
    metadata: ResultMetadata


class ErrorResponse(BaseModel):
    """Uniform error shape returned to clients on failure."""

    error: str
    detail: str
