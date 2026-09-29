"""
Optional URL-based article loading.

This is intentionally a small, isolated extension point (see README /
FUTURE IMPROVEMENTS): fetching a URL and doing best-effort main-content
extraction. It is NOT guaranteed to work for arbitrary websites - pasted
article text remains the primary, reliable V1 workflow.
"""

import asyncio
import ipaddress
import logging
import re
import socket
from urllib.parse import urljoin, urlparse

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)


class ArticleLoadError(ValueError):
    """Raised when a URL cannot be validated or its content cannot be fetched."""


_TAG_SCRIPT_STYLE = re.compile(r"<(script|style|noscript|header|footer|nav)[^>]*>.*?</\1>", re.S | re.I)
_TAG_ANY = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"[ \t]{2,}")
_BLANK_LINES = re.compile(r"\n{3,}")


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ArticleLoadError("Please enter a valid http(s) URL.")


MAX_REDIRECTS = 3


async def _assert_public_host(hostname: str) -> None:
    """
    Reject hosts that resolve to loopback, private, link-local or otherwise
    non-public addresses (basic SSRF protection).
    """
    try:
        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ArticleLoadError("Unable to retrieve the article from this URL.") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ArticleLoadError("Unable to retrieve the article from this URL.")


def _extract_main_text(html: str) -> str:
    """
    Best-effort extraction of readable text from raw HTML.

    This is a lightweight heuristic extractor (strip script/style/nav/footer,
    strip remaining tags, collapse whitespace) rather than a full readability
    algorithm. It works reasonably well for article-style pages but is not
    guaranteed to work for arbitrary, heavily-scripted websites.
    """
    text = _TAG_SCRIPT_STYLE.sub(" ", html)
    text = _TAG_ANY.sub(" ", text)
    text = _WHITESPACE.sub(" ", text)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()


async def load_article_from_url(url: str) -> str:
    """
    Fetch `url` and return best-effort extracted article text.

    Raises ArticleLoadError on invalid URLs, network failures, non-2xx
    responses, or when nothing usable could be extracted.
    """
    _validate_url(url)

    current = url
    try:
        async with httpx.AsyncClient(timeout=settings.url_fetch_timeout) as client:
            for _ in range(MAX_REDIRECTS + 1):
                _validate_url(current)
                await _assert_public_host(urlparse(current).hostname)
                response = await client.get(
                    current, headers={"User-Agent": "ai-article-summarizer/1.0"}
                )
                if response.is_redirect and response.headers.get("location"):
                    current = urljoin(current, response.headers["location"])
                    continue
                break
            else:
                raise ArticleLoadError("Too many redirects while fetching this URL.")
    except httpx.TimeoutException as exc:
        raise ArticleLoadError("Timed out while fetching this URL.") from exc
    except httpx.HTTPError as exc:
        raise ArticleLoadError("Unable to retrieve the article from this URL.") from exc

    if response.status_code >= 400:
        raise ArticleLoadError(
            f"Unable to retrieve the article from this URL (HTTP {response.status_code})."
        )

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type:
        raise ArticleLoadError("This URL does not appear to point to a readable page.")

    text = _extract_main_text(response.text)
    if len(text.split()) < 20:
        raise ArticleLoadError(
            "Could not extract meaningful article content from this URL."
        )

    return text
