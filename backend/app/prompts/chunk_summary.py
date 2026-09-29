from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """\
You are summarizing ONE section (chunk) of a longer article. You do not see \
the whole article - only this section - so summarize only what is here.

Rules:
- Preserve key information, names, and numbers exactly as given.
- Remove repetition and filler language.
- Do not draw conclusions that go beyond what this section states.
- Do not hallucinate information that is not present in this section.
- Keep the summary tight and information-dense.
"""

USER_PROMPT = """\
This is chunk {chunk_index} of an article.

CHUNK TEXT:
{chunk_text}

Summarize this chunk, and list its key points and important facts \
(specific numbers, names, or figures worth preserving).
"""

chunk_summary_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ]
)
