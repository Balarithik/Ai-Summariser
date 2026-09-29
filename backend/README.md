# Backend - AI Article Summarizer

FastAPI + LangChain service implementing the multi-stage summarization
pipeline. See the root `README.md` for architecture and the full pipeline
diagram.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # set OPENAI_API_KEY
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: `http://localhost:8000/docs`.

## Test

```bash
pytest                     # no API key needed
OPENAI_API_KEY=sk-... pytest tests/test_integration.py   # optional live test
```

The suite runs the **real** LangChain chains against a local fake
OpenAI-compatible server (`tests/fake_openai.py`), so prompts, structured
output parsing, ordering, concurrency limits and failure handling are all
exercised without network access. `tests/test_integration.py` only runs
when `OPENAI_API_KEY` is set (and no `OPENAI_BASE_URL` override).

## Layout

| Path | Responsibility |
|---|---|
| `app/prompts/` | Prompt templates only |
| `app/chains/` | One cached LangChain runnable per stage, named for LangSmith |
| `app/services/` | Cleaner, chunker, URL loader, pipeline orchestrator |
| `app/schemas/` | Pydantic request/response and stage-output models |
| `app/llm/provider.py` | The only place chat models are created (cached) |
| `app/config/` | Settings (`settings.py`) and LangSmith wiring (`tracing.py`) |
| `app/api/routes.py` | HTTP layer |

## LangSmith

Set `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY=...` and optionally
`LANGSMITH_PROJECT`. Traces show runs named `article_analysis`,
`chunk_summary`, `chunk_insights`, `synthesis`, `critic`, `final_writer`.

`OPENAI_BASE_URL` (optional) points the client at any OpenAI-compatible
endpoint.
