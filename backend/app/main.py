from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app import db
from app.api.auth import router as auth_router
from app.api.entries import router as entries_router
from app.config import Settings, get_settings
from app.db import Member
from app.deps import current_user


def create_app(settings: Settings | None = None) -> FastAPI:
    """App factory: pass settings to pin a database (tests, scripts).

    Without an argument every request reads `get_settings()`, so env changes and
    dependency overrides keep working.
    """

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        db.init_db((settings or get_settings()).database_path)
        yield

    app = FastAPI(title="API", version="0.1.0", lifespan=lifespan)

    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings

    app.include_router(auth_router)
    app.include_router(entries_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/stats")
    def stats(
        user: Member = Depends(current_user),
        current_settings: Settings = Depends(get_settings),
    ) -> dict[str, int]:
        """Row counts, so "did my data actually persist?" is answerable."""
        return db.stats(current_settings.database_path)

    return app


app = create_app()
