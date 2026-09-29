import socket
import sys
import threading
import time
from pathlib import Path

import pytest
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

from fake_openai import create_fake_openai_app  # noqa: E402

from app.api.rate_limit import limiter  # noqa: E402
from app.chains import clear_chain_caches  # noqa: E402
from app.config.settings import settings  # noqa: E402


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(autouse=True)
def _no_rate_limit_by_default(monkeypatch):
    """Existing tests fire many requests from one client; opt in per test."""
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def fake_llm(monkeypatch):
    """Run a fake OpenAI server and point the real provider at it."""
    app = create_fake_openai_app()
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)

    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_base_url", f"http://127.0.0.1:{port}/v1")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_max_retries", 0)
    clear_chain_caches()

    yield app

    server.should_exit = True
    thread.join(timeout=5)
    clear_chain_caches()
