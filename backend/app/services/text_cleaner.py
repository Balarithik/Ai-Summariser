"""
Text-cleaning service.

Preprocessing only - this deliberately does NOT rewrite or reinterpret the
article's content. It just normalizes whitespace so downstream chunking and
LLM calls receive tidy input.
"""

import re


class TextCleaningError(ValueError):
    """Raised when cleaning results in unusable (empty) text."""


_MULTI_BLANK_LINES = re.compile(r"\n{3,}")
_TRAILING_SPACES = re.compile(r"[ \t]+\n")
_MULTI_SPACES = re.compile(r"[ \t]{2,}")
_MULTI_CARRIAGE_RETURNS = re.compile(r"\r\n?")


def clean_article_text(raw_text: str) -> str:
    """
    Normalize whitespace in `raw_text` while preserving paragraph structure.

    Steps:
    - Normalize line endings to \\n.
    - Strip trailing whitespace from each line.
    - Collapse runs of 2+ spaces/tabs into a single space (within a line).
    - Collapse 3+ consecutive blank lines into exactly one blank line
      (i.e. preserve paragraph breaks, remove excessive gaps).
    - Strip leading/trailing whitespace from the whole document.

    Raises TextCleaningError if the result is empty.
    """
    if raw_text is None:
        raise TextCleaningError("Article text is empty after cleaning.")

    text = _MULTI_CARRIAGE_RETURNS.sub("\n", raw_text)
    text = _TRAILING_SPACES.sub("\n", text)
    lines = [
        _MULTI_SPACES.sub(" ", line) for line in text.split("\n")
    ]
    text = "\n".join(lines)
    text = _MULTI_BLANK_LINES.sub("\n\n", text)
    text = text.strip()

    if not text:
        raise TextCleaningError("Article text is empty after cleaning.")

    return text
