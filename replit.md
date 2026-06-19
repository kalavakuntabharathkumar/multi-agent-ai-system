# Multi-Agent AI Task Automation System

A full-stack AI task automation system with a Next.js frontend and FastAPI backend. It decomposes complex user tasks into subtasks and executes them with specialized LangChain-powered AI agents.

## Architecture

### Python Backend
- **agents/planner.py** — LangChain LCEL planner that creates step-by-step execution plans (knows 5 tools)
- **agents/worker.py** — Executes individual steps using the appropriate tool
- **core/executor.py** — Orchestrates the full run; supports both batch (`run`) and streaming (`run_stream`) execution
- **core/memory.py** — LangChain `InMemoryChatMessageHistory`-backed memory for step outputs
- **tools/text_tools.py** — LangChain LCEL chains for summarize, linkedin_post, email_draft
- **tools/search_tool.py** — DuckDuckGo web search via `DuckDuckGoSearchRun`
- **tools/document_tool.py** — FAISS + OpenAIEmbeddings LCEL retrieval chain for document QA
- **api/main.py** — FastAPI backend (port 8000)

### Next.js Frontend
- **frontend/app/page.tsx** — Single-page UI with SSE real-time streaming of agent steps
- **frontend/next.config.js** — Proxies `/api/*` → `http://localhost:8000/api/*`

## Running

- **Next.js frontend**: `cd frontend && npm run dev` → http://localhost:5000
- **FastAPI backend**: `uvicorn api.main:app --host localhost --port 8000`

## API Endpoints

- `POST /api/run-task` — `{"task": "..."}` returns full result JSON
- `GET /api/run-task/stream?task=...` — Server-Sent Events streaming each step as it completes

## Available Tools

| Tool | Description |
|------|-------------|
| `summarize` | Condense text into a shorter summary |
| `linkedin_post` | Write a professional LinkedIn post from a summary |
| `email_draft` | Draft a concise email from a summary |
| `web_search` | Search the web via DuckDuckGo |
| `document_qa` | Answer questions from a provided document using FAISS retrieval |

## User Preferences

- No OpenAI API key hardcoded — set `OPENAI_API_KEY` environment secret to use live AI features
- LLM clients are lazy-initialized (created on first invocation, not at import time)
