# Multi-Agent AI Task Automation

A real-time multi-agent AI task automation system. Describe a complex task and watch AI agents plan and execute it step by step using Server-Sent Events streaming.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the Express API server (port 8080, proxies to Python backend)
- `pnpm --filter @workspace/multi-agent-ui run dev` — run the React frontend
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- Frontend: React + Vite (artifacts/multi-agent-ui)
- API proxy: Express 5 (artifacts/api-server) — proxies `/api/run-task` to Python FastAPI
- Python backend: FastAPI + LangChain + OpenAI (original, runs separately)
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)

## Where things live

- `artifacts/multi-agent-ui/` — React + Vite frontend (migrated from Next.js)
- `artifacts/api-server/src/routes/run-task.ts` — Express proxy to Python FastAPI backend
- `lib/api-spec/openapi.yaml` — OpenAPI spec (source of truth)
- `.migration-backup/` — original imported project files

## Architecture decisions

- The Express API server proxies `/api/run-task` and `/api/run-task/stream` to the Python FastAPI backend (default: `http://localhost:8000`)
- SSE streaming is pass-through proxied via Express fetch + ReadableStream
- `PYTHON_BACKEND_URL` env var controls the Python backend URL (default: `http://localhost:8000`)
- Frontend uses `import.meta.env.BASE_URL` prefix for all API calls (Replit path routing)
- Next.js App Router → wouter + single `src/pages/home.tsx` component

## Product

- Users enter a natural language task description
- A planner agent (LangChain LCEL + OpenAI) decomposes it into ordered steps
- Worker agents execute each step using 5 tools: summarize, linkedin_post, email_draft, web_search, document_qa
- Results stream in real-time via Server-Sent Events
- Color-coded tool badges, step metadata, live status indicators

## Setup — Python Backend

The frontend works independently, but to actually run agent tasks you need the Python backend:

```bash
# Set your OpenAI key
export OPENAI_API_KEY=sk-...

# Start the FastAPI server (from project root)
pip install -r requirements.txt
uvicorn api.main:app --host localhost --port 8000 --reload
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key (for Python backend) |
| `PYTHON_BACKEND_URL` | No | Python backend URL (default: `http://localhost:8000`) |

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- The Node.js Express server proxies to Python FastAPI — both need to run for task execution to work
- SSE streaming is proxied end-to-end through Express; response buffering must be disabled (`X-Accel-Buffering: no`)
- `OPENAI_API_KEY` is consumed by the Python backend, not the Node.js server

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
