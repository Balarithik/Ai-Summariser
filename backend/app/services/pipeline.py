"""
Pipeline orchestrator.

`ArticleSummarizationPipeline` coordinates the stages defined in
app/chains and app/services, but contains no prompt strings and no LLM
instantiation of its own - it only sequences calls and handles
concurrency, ordering, and failure recovery.

Stage order:
    validate -> clean -> chunk -> analyze
             -> (parallel per-chunk: summary + insights)
             -> synthesize -> critique -> (optional revise) -> final write
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass

from app.chains.analysis import run_analysis
from app.chains.chunk_summary import run_chunk_summary
from app.chains.critic import run_critic
from app.chains.final_writer import run_final_writer
from app.chains.insights import run_insights
from app.chains.synthesis import run_synthesis
from app.config.settings import settings
from app.llm.errors import ProviderError, classify_exception
from app.schemas.analysis import ChunkResult, FinalSummary
from app.services.chunker import chunk_article
from app.services.text_cleaner import TextCleaningError, clean_article_text

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _stage(name: str):
    """Log stage start/completion/failure with duration."""
    started = time.monotonic()
    logger.info("Stage started: %s", name)
    try:
        yield
    except Exception:
        logger.error("Stage failed: %s after %.2fs", name, time.monotonic() - started)
        raise
    logger.info("Stage completed: %s in %.2fs", name, time.monotonic() - started)


class InputValidationError(ValueError):
    """Raised when the incoming article fails validation checks."""


@dataclass
class PipelineResult:
    final_summary: FinalSummary
    input_words: int
    chunk_count: int
    revised: bool
    duration_seconds: float


def validate_article_text(article: str) -> None:
    """Raise InputValidationError with a user-facing message if invalid."""
    if not article or not article.strip():
        raise InputValidationError("Please enter an article.")

    word_count = len(article.split())
    if word_count < settings.min_article_words:
        raise InputValidationError(
            f"Article is too short to summarize. Please provide at least "
            f"{settings.min_article_words} words (got {word_count})."
        )

    if len(article) > settings.max_article_chars:
        raise InputValidationError(
            f"Article is too long. Please provide fewer than "
            f"{settings.max_article_chars} characters."
        )


async def _process_chunk(index: int, text: str, semaphore: asyncio.Semaphore) -> ChunkResult:
    """Run chunk summary and insight extraction concurrently for one chunk."""
    async with semaphore:
        summary_task = asyncio.create_task(run_chunk_summary(index, text))
        insights_task = asyncio.create_task(run_insights(index, text))
        summary_result, insights_result = await asyncio.gather(
            summary_task, insights_task, return_exceptions=True
        )

    result = ChunkResult(chunk_index=index)

    if isinstance(summary_result, Exception):
        provider_error = classify_exception(summary_result)
        logger.error("Chunk %s summary failed: %s", index, provider_error.message)
        result.summary_error = provider_error.message
    else:
        result.summary = summary_result

    if isinstance(insights_result, Exception):
        provider_error = classify_exception(insights_result)
        logger.error("Chunk %s insights failed: %s", index, provider_error.message)
        result.insights_error = provider_error.message
    else:
        result.insights = insights_result

    return result


class ArticleSummarizationPipeline:
    """Coordinates the full multi-stage summarization pipeline."""

    def __init__(self, max_concurrency: int | None = None) -> None:
        self._max_concurrency = max_concurrency or settings.max_concurrency

    async def run(self, article: str, summary_length: str) -> PipelineResult:
        start = time.monotonic()

        # 1. Validate
        validate_article_text(article)
        input_words = len(article.split())
        logger.info("Pipeline started. input_words=%s summary_length=%s", input_words, summary_length)

        # 2. Clean
        try:
            cleaned = clean_article_text(article)
        except TextCleaningError as exc:
            raise InputValidationError(str(exc)) from exc

        # 3. Chunk
        chunks = chunk_article(cleaned)
        if not chunks:
            raise InputValidationError("Please enter an article.")
        chunk_count = len(chunks)
        logger.info("Chunking complete. chunk_count=%s", chunk_count)

        # 4. Analyze (whole-article context)
        async with _stage("article_analysis"):
            try:
                analysis = await run_analysis(cleaned)
            except Exception as exc:
                raise classify_exception(exc) from exc

        # 5. Parallel per-chunk processing (summary + insights)
        async with _stage("chunk_summary+chunk_insights"):
            semaphore = asyncio.Semaphore(self._max_concurrency)
            chunk_results = await asyncio.gather(
                *[
                    _process_chunk(i, chunk_text, semaphore)
                    for i, chunk_text in enumerate(chunks)
                ]
            )
            chunk_results = sorted(chunk_results, key=lambda c: c.chunk_index)

        # If every chunk failed on both chains there is nothing to synthesize.
        if all(c.summary is None and c.insights is None for c in chunk_results):
            raise ProviderError("All chunk processing failed.")

        # 6. Synthesis
        async with _stage("synthesis"):
            try:
                draft = await run_synthesis(analysis, chunk_results)
            except Exception as exc:
                raise classify_exception(exc) from exc

        # 7. Critique
        async with _stage("critic"):
            try:
                critique = await run_critic(cleaned, draft)
            except Exception as exc:
                raise classify_exception(exc) from exc
        logger.info("Critic verdict: %s", critique.status)

        # 8. Optional single revision cycle: if REVISE, the final writer is
        #    given the critique to address. We do not loop back to the
        #    critic again - maximum one revision cycle in V1.
        revised = critique.status == "REVISE"

        # 9. Final writer
        async with _stage("final_writer"):
            try:
                final_summary = await run_final_writer(analysis, draft, critique, summary_length)
            except Exception as exc:
                raise classify_exception(exc) from exc

        duration = time.monotonic() - start
        logger.info("Pipeline finished. duration_seconds=%.2f", duration)

        return PipelineResult(
            final_summary=final_summary,
            input_words=input_words,
            chunk_count=chunk_count,
            revised=revised,
            duration_seconds=duration,
        )
