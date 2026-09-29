"""Critic chain: original article + draft summary -> CritiqueResult."""

from functools import lru_cache

from langchain_core.runnables import Runnable

from app.llm.provider import create_chat_model
from app.prompts.critic import critic_prompt
from app.schemas.analysis import CritiqueResult, DraftSummary


@lru_cache(maxsize=1)
def build_critic_chain() -> Runnable:
    model = create_chat_model(temperature=0).with_structured_output(CritiqueResult)
    return (critic_prompt | model).with_config(run_name="critic", tags=["critic"])


async def run_critic(article: str, draft: DraftSummary) -> CritiqueResult:
    chain = build_critic_chain()
    result = await chain.ainvoke({"article": article, "draft_summary": draft.draft_summary})
    status = (result.status or "").strip().upper()
    if status not in ("PASS", "REVISE"):
        # Defensive normalization if the model returns an unexpected value.
        has_problems = bool(result.issues or result.missing_points or result.unsupported_claims)
        status = "REVISE" if has_problems else "PASS"
    result.status = status
    return result
