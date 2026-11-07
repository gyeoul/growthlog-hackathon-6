# Assistant — Next.js + FastAPI conversational app

A minimal, working conversational web app: a streaming chat UI on Next.js
(App Router, TypeScript, Tailwind v4) talking to a FastAPI backend over SSE.
The backend proxies any OpenAI-compatible chat API — local Ollama by default.

```
browser ──▶ Next.js :3000 ──(rewrite /api/*)──▶ FastAPI :8000 ──▶ LLM
```

Going through the Next.js rewrite keeps the browser on one origin, so there is
no CORS to configure and no API base URL to inject into the client bundle.

## Requirements

- Node.js 20+ (24 tested) and pnpm
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- An OpenAI-compatible LLM endpoint (Ollama on `localhost:11434` by default)

## Run

```bash
# 1) Backend
cd backend
cp .env.example .env          # adjust LLM_MODEL if needed
ollama pull llama3.2          # only needed for the default config
uv sync
uv run uvicorn app.main:app --reload --port 8000

# 2) Frontend (separate terminal)
cd frontend
pnpm install
pnpm dev                      # http://localhost:3000
```

## Configuration

Backend reads `backend/.env` (see `.env.example`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible base URL |
| `LLM_API_KEY` | `ollama` | Bearer token (`sk-…` for OpenAI) |
| `LLM_MODEL` | `llama3.2` | Model name passed to the API |
| `LLM_TIMEOUT` | `120` | Seconds per request |
| `SYSTEM_PROMPT` | short helper prompt | Prepended to every conversation |
| `CORS_ORIGINS` | `http://localhost:3000` | Only needed if you call the API from another origin |

Frontend reads `BACKEND_URL` (default `http://127.0.0.1:8000`) when proxying `/api/*`.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness + active model |
| `POST` | `/api/chat` | Non-streaming completion → `{content, model}` |
| `POST` | `/api/chat/stream` | SSE: `data: {"delta": "..."}` … `data: [DONE]` |

Errors surface as `502` (non-streaming) or an in-band `data: {"error": "..."}`
frame (streaming), so a dropped model never hangs the UI. If FastAPI itself is
down the proxy returns an HTML 500; the client turns that into an actionable
message instead of a raw HTML body.

Interactive docs: <http://localhost:8000/docs>

## Layout

```
backend/
  app/main.py            app factory, CORS, router
  app/config.py          pydantic-settings configuration
  app/schemas.py         request/response models
  app/api/chat.py        /api endpoints (incl. SSE)
  app/services/llm.py    OpenAI-compatible client (stream + complete)
  tests/test_api.py      contract tests, LLM mocked
frontend/
  next.config.ts         /api/* → FastAPI rewrite
  src/lib/api.ts         typed SSE stream reader + error translation
  src/components/chat.tsx  chat UI (streaming, stop, empty state, autoscroll)
  src/components/markdown.tsx  sanitized markdown rendering for replies
  src/app/page.tsx       page shell
```

## Test

```bash
cd backend && uv run pytest
cd frontend && pnpm lint && pnpm build
```
