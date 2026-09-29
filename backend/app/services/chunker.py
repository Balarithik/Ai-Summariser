"""
Chunking service.

Wraps LangChain's RecursiveCharacterTextSplitter with settings-driven
configuration and guarantees the app never has to deal with empty chunks.
"""

from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config.settings import settings


def chunk_article(
    text: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[str]:
    """
    Split `text` into ordered, non-empty chunks.

    Uses settings.chunk_size / settings.chunk_overlap unless overridden.
    """
    size = chunk_size if chunk_size is not None else settings.chunk_size
    overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    raw_chunks = splitter.split_text(text)
    chunks = [chunk.strip() for chunk in raw_chunks if chunk and chunk.strip()]

    if not chunks:
        # Extremely short input that still passed validation - treat the
        # whole text as a single chunk rather than producing nothing.
        return [text.strip()] if text.strip() else []

    return chunks
