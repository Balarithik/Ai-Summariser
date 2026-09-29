from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """\
You are synthesizing a single, coherent, article-level summary from \
per-section summaries and analytical insights that were produced \
independently and out of context of each other.

Rules:
- Do NOT simply concatenate the chunk summaries - merge and re-write them \
into one coherent narrative.
- Combine related ideas that appear in multiple chunks into a single \
statement.
- Remove duplicate points.
- Preserve the article's central argument as identified in the analysis.
- Preserve important facts and figures.
- Maintain a logical order (the order the article actually develops ideas \
in, not necessarily chunk order if ideas span chunks).
- Do not introduce any information that is not supported by the provided \
material.
"""

USER_PROMPT = """\
ARTICLE ANALYSIS:
Topic: {topic}
Main argument: {main_argument}
Key points: {analysis_key_points}
Conclusion: {analysis_conclusion}

PER-SECTION SUMMARIES (in original order):
{chunk_summaries}

PER-SECTION ANALYTICAL INSIGHTS (in original order):
{chunk_insights}

Synthesize these into one coherent, non-redundant, article-level draft \
summary, along with a consolidated list of key points and important facts.
"""

synthesis_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ]
)
