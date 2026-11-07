# hackerton-11 — Next.js + FastAPI skeleton

Minimal starting point for a web app with a Next.js frontend and a FastAPI
backend. No features beyond a health check; add your own.

```
browser ──▶ Next.js :3000 ──(rewrite /api/*)──▶ FastAPI :8000
```

The Next.js rewrite proxies `/api/*` to FastAPI, so the browser only ever talks
to one origin: no CORS setup, no API base URL in the client bundle.

## Requirements

- Node.js 20+ and pnpm
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)

## Run

```bash
# 1) Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

# 2) Frontend (separate terminal)
cd frontend
pnpm install
pnpm dev                      # http://localhost:3000
```

Or both at once from the repo root:

```bash
make setup    # uv sync + pnpm install
make dev      # backend on :8000, frontend on :3000
```

## Configuration

Frontend reads `BACKEND_URL` (default `http://127.0.0.1:8000`) when proxying
`/api/*` — set it in `frontend/.env.local` to point elsewhere.

## Layout

```
backend/
  app/main.py          FastAPI app; add routers here
  tests/test_api.py    pytest, uses Starlette's TestClient
frontend/
  next.config.ts       /api/* → FastAPI rewrite
  src/app/page.tsx     placeholder page
  src/app/globals.css  Tailwind v4 theme tokens (--bg, --fg, --muted, …)
Makefile               setup / dev / test / build / clean
```

## Test

```bash
cd backend && uv run pytest
cd frontend && pnpm lint && pnpm build
```
