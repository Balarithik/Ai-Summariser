"""
Minimal fake OpenAI-compatible chat-completions server for tests.

It lets the REAL LangChain chains (prompt -> ChatOpenAI -> structured output
parsing) run end to end without network access or a paid API key. The
schema being requested is detected from the request (json_schema response
format or a forced tool call) and a canned, schema-valid answer is returned.
"""

import json
import time
from typing import Any, Dict, List

from fastapi import FastAPI, Request

CANNED: Dict[str, Dict[str, Any]] = {
    "ArticleAnalysis": {
        "topic": "AI in software engineering",
        "main_argument": "AI tooling is reshaping how software is built.",
        "key_points": ["Tooling adoption is rising", "Review remains essential"],
        "entities": ["OpenAI"],
        "conclusion": "Teams should adopt AI carefully.",
    },
    "ChunkSummary": {
        "chunk_index": 0,
        "summary": "This section discusses tooling adoption.",
        "key_points": ["Adoption is rising"],
        "important_facts": ["Adoption grew 40%"],
    },
    "ChunkInsights": {
        "chunk_index": 0,
        "claims": ["AI speeds up delivery"],
        "evidence": ["Survey of engineers"],
        "statistics": ["40% growth"],
        "cause_effect": ["Better tools lead to faster delivery"],
        "problems": ["Over-reliance"],
        "solutions": ["Human review"],
        "observations": [],
    },
    "DraftSummary": {
        "draft_summary": "AI tooling is reshaping software engineering.",
        "key_points": ["Adoption is rising"],
        "important_facts": ["Adoption grew 40%"],
    },
    "CritiqueResult": {
        "status": "PASS",
        "issues": [],
        "missing_points": [],
        "unsupported_claims": [],
        "recommendations": [],
    },
    "FinalSummary": {
        "title": "How AI Is Reshaping Software Engineering",
        "summary": "AI tooling is changing how teams build software, with adoption rising quickly while human review stays essential.",
        "key_points": ["Adoption is rising", "Review remains essential"],
        "main_argument": "AI tooling is reshaping how software is built.",
        "important_facts": ["Adoption grew 40%"],
        "conclusion": "Teams should adopt AI carefully.",
        "word_count": 0,
    },
}


def create_fake_openai_app(critic_status: str = "PASS") -> FastAPI:
    app = FastAPI()
    app.state.requests: List[dict] = []
    app.state.critic_status = critic_status
    app.state.fail_schema = None  # schema name that should return HTTP 500

    def _schema_name(body: dict) -> str | None:
        rf = body.get("response_format") or {}
        if rf.get("type") == "json_schema":
            return rf["json_schema"]["name"]
        for tool in body.get("tools") or []:
            return tool["function"]["name"]
        return None

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        body = await request.json()
        name = _schema_name(body)
        app.state.requests.append({"schema": name, "body": body})

        if name and name == app.state.fail_schema:
            from fastapi.responses import JSONResponse

            return JSONResponse({"error": {"message": "boom"}}, status_code=500)

        payload = dict(CANNED.get(name, {}))
        if name == "CritiqueResult":
            payload["status"] = app.state.critic_status
            if payload["status"] == "REVISE":
                payload["issues"] = ["Missing the adoption statistic"]
                payload["recommendations"] = ["Mention the 40% growth"]

        message: Dict[str, Any] = {"role": "assistant", "content": None}
        finish = "stop"
        if (body.get("response_format") or {}).get("type") == "json_schema":
            message["content"] = json.dumps(payload)
        elif body.get("tools"):
            message["tool_calls"] = [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(payload)},
                }
            ]
            finish = "tool_calls"
        else:
            message["content"] = json.dumps(payload)

        return {
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.get("model", "fake"),
            "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

    return app
