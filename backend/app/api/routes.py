"""API routes."""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.article import SummarizeRequest
from app.schemas.result import ResultMetadata, SummarizeResponse
from app.services.article_loader import ArticleLoadError, load_article_from_url
from app.services.pipeline import ArticleSummarizationPipeline, InputValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["summarization"])

pipeline = ArticleSummarizationPipeline()


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    responses={400: {"description": "Invalid input"}, 502: {"description": "AI service error"}},
)
async def summarize(request: SummarizeRequest) -> SummarizeResponse:
    article_text = request.article

    if not article_text and request.url:
        try:
            article_text = await load_article_from_url(request.url)
        except ArticleLoadError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not article_text:
        raise HTTPException(status_code=400, detail="Please enter an article.")

    try:
        result = await pipeline.run(article_text, request.summary_length.value)
    except InputValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - convert all unexpected errors safely
        logger.exception("Pipeline execution failed")
        raise HTTPException(
            status_code=502,
            detail="The AI service is temporarily unavailable. Please try again.",
        ) from exc

    final = result.final_summary
    return SummarizeResponse(
        title=final.title,
        summary=final.summary,
        key_points=final.key_points,
        main_argument=final.main_argument,
        important_facts=final.important_facts,
        conclusion=final.conclusion,
        word_count=final.word_count,
        metadata=ResultMetadata(
            input_words=result.input_words,
            chunk_count=result.chunk_count,
            revised=result.revised,
            duration_seconds=round(result.duration_seconds, 2),
        ),
    )


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
