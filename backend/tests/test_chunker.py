from app.services.chunker import chunk_article


def test_short_text_returns_single_chunk():
    text = "This is a short article about testing." * 3
    chunks = chunk_article(text, chunk_size=4000, chunk_overlap=400)
    assert len(chunks) == 1
    assert chunks[0]


def test_long_text_produces_multiple_chunks():
    # ~10 * 500 = 5000 chars, well beyond a 1000-char chunk size.
    paragraph = "Sentence number {} in a long article. ".format
    text = "\n\n".join(paragraph(i) * 20 for i in range(10))
    chunks = chunk_article(text, chunk_size=1000, chunk_overlap=100)
    assert len(chunks) > 1


def test_no_empty_chunks_produced():
    text = "Word " * 2000
    chunks = chunk_article(text, chunk_size=500, chunk_overlap=50)
    assert all(chunk.strip() for chunk in chunks)


def test_chunks_preserve_order_via_reconstruction():
    # Chunks should appear in the same order as they occur in the source text.
    text = "\n\n".join(f"Paragraph number {i} of the article." for i in range(20))
    chunks = chunk_article(text, chunk_size=100, chunk_overlap=0)
    search_from = 0
    for chunk in chunks:
        first_line = chunk.split("\n")[0]
        idx = text.find(first_line, search_from)
        assert idx != -1
        search_from = idx


def test_empty_text_returns_no_chunks():
    assert chunk_article("") == []
