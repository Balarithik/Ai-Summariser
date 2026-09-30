"""API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.rate_limit import enforce_rate_limit
from app.llm.errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderError,
    ProviderQuotaExhaustedError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    classify_exception,
)
from app.schemas.article import SummarizeRequest
from app.schemas.result import ResultMetadata, SummarizeResponse
from app.services.article_loader import ArticleLoadError, load_article_from_url
from app.services.pipeline import ArticleSummarizationPipeline, InputValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["summarization"])

pipeline = ArticleSummarizationPipeline()


def _map_provider_error(exc: ProviderError) -> HTTPException:
    """Map a ProviderError to an appropriate HTTPException."""
    if isinstance(exc, ProviderConfigurationError):
        return HTTPException(status_code=500, detail=exc.message)
    if isinstance(exc, ProviderAuthenticationError):
        return HTTPException(status_code=500, detail=exc.message)
    if isinstance(exc, ProviderQuotaExhaustedError):
        return HTTPException(status_code=500, detail=exc.message)
    if isinstance(exc, ProviderRateLimitError):
        return HTTPException(status_code=429, detail=exc.message)
    if isinstance(exc, ProviderTimeoutError):
        return HTTPException(status_code=504, detail=exc.message)
    return HTTPException(status_code=502, detail=exc.message)


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    dependencies=[Depends(enforce_rate_limit)],
    responses={
        400: {"description": "Invalid input"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Provider configuration or quota error"},
        502: {"description": "AI service error"},
        504: {"description": "AI service timeout"},
    },
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
    except ProviderError as exc:
        logger.error("Provider error: %s", exc.message)
        raise _map_provider_error(exc) from exc
    except Exception as exc:  # noqa: BLE001 - convert all unexpected errors safely
        logger.exception("Pipeline execution failed")
        provider_error = classify_exception(exc)
        raise _map_provider_error(provider_error) from exc

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
