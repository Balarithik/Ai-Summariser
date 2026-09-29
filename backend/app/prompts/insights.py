from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """\
You are an analytical reader extracting structured insight from ONE section \
(chunk) of a longer article. This is NOT a summarization task - you are \
extracting claims, evidence, statistics, cause-and-effect relationships, \
problems, and solutions.

Rules:
- Only extract what is explicitly present in this chunk.
- Distinguish claims from the evidence offered for them.
- Capture numeric data points verbatim where possible.
- Do not repeat the same idea across multiple fields unless it genuinely \
belongs to more than one category.
- If a category has no relevant content in this chunk, return an empty list \
for it - do not invent content to fill it.
"""

USER_PROMPT = """\
This is chunk {chunk_index} of an article.

CHUNK TEXT:
{chunk_text}

Extract the analytical structure of this chunk: claims, evidence, \
statistics, cause-and-effect relationships, problems raised, solutions \
proposed, and any other notable observations.
"""

insights_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ]
)
