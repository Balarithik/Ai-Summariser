import os

from app.config.settings import Settings
from app.config.tracing import configure_tracing


def _clear(monkeypatch):
    for k in ("LANGSMITH_TRACING", "LANGSMITH_API_KEY", "LANGSMITH_PROJECT"):
        monkeypatch.delenv(k, raising=False)


def test_tracing_disabled_by_default(monkeypatch):
    _clear(monkeypatch)
    assert configure_tracing(Settings(_env_file=None)) is False
    assert "LANGSMITH_TRACING" not in os.environ


def test_tracing_requires_key(monkeypatch):
    _clear(monkeypatch)
    assert configure_tracing(Settings(_env_file=None, LANGSMITH_TRACING="true")) is False


def test_tracing_enabled_exports_env(monkeypatch):
    _clear(monkeypatch)
    cfg = Settings(_env_file=None, LANGSMITH_TRACING="true", LANGSMITH_API_KEY="k", LANGSMITH_PROJECT="proj")
    assert configure_tracing(cfg) is True
    assert os.environ["LANGSMITH_PROJECT"] == "proj"
    for k in ("LANGSMITH_TRACING", "LANGSMITH_API_KEY", "LANGSMITH_PROJECT"):
        monkeypatch.delenv(k, raising=False)


def test_chain_run_names_match_stage_names():
    from app.chains import (
        build_analysis_chain, build_chunk_summary_chain, build_critic_chain,
        build_final_writer_chain, build_insights_chain, build_synthesis_chain,
    )

    expected = {
        build_analysis_chain: "article_analysis",
        build_chunk_summary_chain: "chunk_summary",
        build_insights_chain: "chunk_insights",
        build_synthesis_chain: "synthesis",
        build_critic_chain: "critic",
        build_final_writer_chain: "final_writer",
    }
    for builder, name in expected.items():
        assert builder().config["run_name"] == name
