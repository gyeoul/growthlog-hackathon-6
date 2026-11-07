.PHONY: setup dev api web test build clean fake-idp doctor

setup:            ## install both toolchains
	cd backend && uv sync
	cd frontend && pnpm install

dev:              ## run backend + frontend together (Ctrl-C stops both)
	@echo "backend :8000  frontend :3000"
	@trap 'kill 0' INT TERM EXIT; \
		(cd backend && uv run uvicorn app.main:app --reload --port 8000) & \
		(cd frontend && pnpm dev) & \
		wait

api:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

web:
	cd frontend && pnpm dev

fake-idp:         ## fake Google IdP on :8099 for login testing without credentials
	python3 scripts/fake_idp.py

doctor:           ## check that both servers answer and auth is configured
	@curl -fsS -m 3 http://127.0.0.1:8000/api/health >/dev/null \
		&& echo "backend  :8000 ok" \
		|| echo "backend  :8000 DOWN  -> make api (a 500 on /api/* means this)"
	@curl -fsS -m 3 -o /dev/null http://127.0.0.1:3000 \
		&& echo "frontend :3000 ok" \
		|| echo "frontend :3000 DOWN  -> make web"
	@cd backend && uv run python -c "from app.config import get_settings; s=get_settings(); print('database :', s.database_path); print('google   :', 'configured' if s.google_configured else 'MISSING (logins redirect to ?auth_error=config)')"

test:
	cd backend && uv run pytest

build:
	cd frontend && pnpm lint && pnpm build

clean:
	rm -rf frontend/.next backend/.pytest_cache
	find backend -name __pycache__ -type d -prune -exec rm -rf {} +
