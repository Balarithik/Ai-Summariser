"""Article-level analysis chain: article text -> ArticleAnalysis."""

from functools import lru_cache

from langchain_core.runnables import Runnable

from app.llm.provider import create_chat_model
from app.prompts.analysis import analysis_prompt
from app.schemas.analysis import ArticleAnalysis


@lru_cache(maxsize=1)
def build_analysis_chain() -> Runnable:
    """Return a runnable: {"article": str} -> ArticleAnalysis."""
    model = create_chat_model().with_structured_output(ArticleAnalysis)
    return (analysis_prompt | model).with_config(run_name="article_analysis", tags=["article_analysis"])


async def run_analysis(article: str) -> ArticleAnalysis:
    chain = build_analysis_chain()
    result = await chain.ainvoke({"article": article})
    return result
