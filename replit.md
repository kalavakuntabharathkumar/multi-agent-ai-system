# Multi-Agent AI Task Automation System

A Python application that decomposes complex user tasks into subtasks and executes them with specialized AI agents.

## Architecture

- **agents/planner.py** — LangChain-powered planner that creates step-by-step execution plans
- **agents/worker.py** — Executes individual steps using the appropriate tool
- **core/executor.py** — Orchestrates the full run, supports both batch and streaming execution
- **core/memory.py** — LangChain `InMemoryChatMessageHistory`-backed memory for step outputs
- **tools/text_tools.py** — LangChain LCEL chains for summarize, linkedin_post, email_draft
- **interface/app.py** — Streamlit web UI (runs on port 5000)
- **api/main.py** — FastAPI backend (runs on port 8000)

## Running

- **Streamlit UI**: `streamlit run interface/app.py` → http://localhost:5000
- **FastAPI backend**: `uvicorn api.main:app --host localhost --port 8000`

## API Endpoints

- `POST /api/run-task` — `{"task": "..."}` returns full result JSON
- `GET /api/run-task/stream?task=...` — Server-Sent Events streaming each step as it completes

## User Preferences

- No OpenAI API key hardcoded — set `OPENAI_API_KEY` environment secret to use live AI features
- LLM clients are lazy-initialized (created on first invocation, not at import time)
