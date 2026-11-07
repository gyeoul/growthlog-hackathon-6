.PHONY: setup dev api web test build clean

setup:            ## install both toolchains
	cd backend && uv sync
	cd frontend && pnpm install

dev:              ## run backend + frontend together
	@$(MAKE) -j2 api web

api:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

web:
	cd frontend && pnpm dev

test:
	cd backend && uv run pytest

build:
	cd frontend && pnpm lint && pnpm build

clean:
	rm -rf frontend/.next backend/.pytest_cache
	find backend -name __pycache__ -type d -prune -exec rm -rf {} +
