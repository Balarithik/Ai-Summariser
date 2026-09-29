"""LangSmith tracing configuration (environment-driven, optional)."""

import logging
import os

from app.config.settings import Settings, settings as default_settings

logger = logging.getLogger(__name__)


def configure_tracing(cfg: Settings | None = None) -> bool:
    """
    Export LangSmith env vars if tracing is enabled AND a key is present.

    LangChain reads tracing configuration from process environment
    variables, so we translate our settings into them. Returns True when
    tracing was enabled. The API key is never logged.
    """
    cfg = cfg or default_settings
    if not cfg.langsmith_tracing:
        return False
    if not cfg.langsmith_api_key:
        logger.warning("LANGSMITH_TRACING is enabled but LANGSMITH_API_KEY is missing; tracing disabled.")
        return False

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = cfg.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = cfg.langsmith_project
    logger.info("LangSmith tracing enabled. project=%s", cfg.langsmith_project)
    return True
