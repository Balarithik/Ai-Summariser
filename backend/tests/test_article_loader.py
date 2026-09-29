import httpx
import pytest

from app.services import article_loader
from app.services.article_loader import ArticleLoadError, load_article_from_url

PAGE = "<html><nav>menu</nav><body><p>" + "Real article sentence here. " * 40 + "</p><script>x()</script></body></html>"


@pytest.fixture(autouse=True)
def public_host(monkeypatch):
    async def ok(hostname):
        return None

    monkeypatch.setattr(article_loader, "_assert_public_host", ok)


def _mock_client(monkeypatch, handler):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(article_loader.httpx, "AsyncClient", factory)


async def test_extracts_article_text(monkeypatch):
    _mock_client(monkeypatch, lambda r: httpx.Response(200, text=PAGE, headers={"content-type": "text/html"}))
    text = await load_article_from_url("https://example.com/a")
    assert "Real article sentence" in text
    assert "menu" not in text and "x()" not in text


@pytest.mark.parametrize("url", ["ftp://example.com/x", "not a url", "javascript:alert(1)", "https://"])
async def test_rejects_invalid_urls(url):
    with pytest.raises(ArticleLoadError):
        await load_article_from_url(url)


async def test_http_error_status(monkeypatch):
    _mock_client(monkeypatch, lambda r: httpx.Response(404, text="nope", headers={"content-type": "text/html"}))
    with pytest.raises(ArticleLoadError, match="404"):
        await load_article_from_url("https://example.com/missing")


async def test_timeout(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("slow")

    _mock_client(monkeypatch, handler)
    with pytest.raises(ArticleLoadError, match="Timed out"):
        await load_article_from_url("https://example.com/slow")


async def test_non_text_content_rejected(monkeypatch):
    _mock_client(monkeypatch, lambda r: httpx.Response(200, content=b"\x00", headers={"content-type": "image/png"}))
    with pytest.raises(ArticleLoadError):
        await load_article_from_url("https://example.com/img")


async def test_thin_page_rejected(monkeypatch):
    _mock_client(monkeypatch, lambda r: httpx.Response(200, text="<p>hi</p>", headers={"content-type": "text/html"}))
    with pytest.raises(ArticleLoadError, match="meaningful"):
        await load_article_from_url("https://example.com/thin")


async def test_redirect_to_private_host_blocked(monkeypatch):
    async def guard(hostname):
        if hostname == "internal.local":
            raise ArticleLoadError("blocked")

    monkeypatch.setattr(article_loader, "_assert_public_host", guard)

    def handler(request):
        if request.url.host == "example.com":
            return httpx.Response(302, headers={"location": "http://internal.local/secret"})
        return httpx.Response(200, text=PAGE, headers={"content-type": "text/html"})

    _mock_client(monkeypatch, handler)
    with pytest.raises(ArticleLoadError):
        await load_article_from_url("https://example.com/redir")


async def test_too_many_redirects(monkeypatch):
    _mock_client(monkeypatch, lambda r: httpx.Response(302, headers={"location": "https://example.com/again"}))
    with pytest.raises(ArticleLoadError, match="redirect"):
        await load_article_from_url("https://example.com/loop")


async def test_real_ssrf_guard_blocks_loopback(monkeypatch):
    monkeypatch.undo()  # restore the real _assert_public_host
    for host in ("127.0.0.1", "localhost", "169.254.169.254", "10.0.0.5"):
        with pytest.raises(ArticleLoadError):
            await article_loader._assert_public_host(host)
