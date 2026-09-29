"""Request-side schemas: what the client sends us."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SummaryLength(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    DETAILED = "detailed"


class SummarizeRequest(BaseModel):
    """Body of POST /api/v1/summarize."""

    article: Optional[str] = Field(
        default=None, description="Raw article text to summarize."
    )
    url: Optional[str] = Field(
        default=None, description="Optional URL to fetch article text from."
    )
    summary_length: SummaryLength = Field(
        default=SummaryLength.MEDIUM,
        description="Desired level of detail: short, medium, or detailed.",
    )

    @field_validator("article")
    @classmethod
    def _strip_article(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return value.strip()

    @field_validator("url")
    @classmethod
    def _strip_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        return value or None
