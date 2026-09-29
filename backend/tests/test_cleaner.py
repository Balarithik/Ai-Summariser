import pytest

from app.services.text_cleaner import TextCleaningError, clean_article_text


def test_collapses_multiple_spaces():
    assert clean_article_text("Hello    world") == "Hello world"


def test_strips_trailing_whitespace_per_line():
    result = clean_article_text("Line one   \nLine two")
    assert result == "Line one\nLine two"


def test_preserves_paragraph_breaks():
    text = "Paragraph one.\n\nParagraph two."
    assert clean_article_text(text) == text


def test_collapses_excessive_blank_lines():
    text = "Para one.\n\n\n\n\nPara two."
    assert clean_article_text(text) == "Para one.\n\nPara two."


def test_strips_leading_and_trailing_whitespace():
    result = clean_article_text("   \n\nSome text here.\n\n   ")
    assert result == "Some text here."


def test_normalizes_windows_line_endings():
    result = clean_article_text("Line one\r\nLine two\r\n")
    assert "\r" not in result


def test_raises_on_empty_result():
    with pytest.raises(TextCleaningError):
        clean_article_text("     \n\n   ")


def test_raises_on_none_input():
    with pytest.raises(TextCleaningError):
        clean_article_text(None)
