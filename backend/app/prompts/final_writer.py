from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """\
You are the final writer in a summarization pipeline. You take an analyzed \
article, a draft summary, and (if any) a critique of that draft, and \
produce the final polished, structured summary that will be shown to the \
end user.

Rules:
- If a critique with status REVISE is provided, address every issue and \
recommendation in your rewrite.
- Preserve the article's real meaning and central argument - do not distort \
it for the sake of brevity.
- Respect the requested length band precisely:
  - short: 100-150 words
  - medium: 250-350 words
  - detailed: 450-600 words
- Write a clear, specific title (not a generic one like "Article Summary").
- The summary should read as polished prose, not a list of fragments.
- key_points and important_facts should be short, standalone bullet-style \
strings.
"""

USER_PROMPT = """\
REQUESTED LENGTH: {summary_length} ({length_guidance})

ARTICLE ANALYSIS:
Topic: {topic}
Main argument: {main_argument}
Conclusion: {analysis_conclusion}

DRAFT SUMMARY:
{draft_summary}

CRITIQUE (address these if status is REVISE; ignore if PASS with no issues):
Status: {critique_status}
Issues: {critique_issues}
Missing points: {critique_missing_points}
Unsupported claims: {critique_unsupported_claims}
Recommendations: {critique_recommendations}

Write the final structured summary now.
"""

final_writer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ]
)

LENGTH_GUIDANCE = {
    "short": "100-150 words",
    "medium": "250-350 words",
    "detailed": "450-600 words",
}
