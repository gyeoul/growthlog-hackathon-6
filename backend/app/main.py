from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.api.auth import router as auth_router
from app.config import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db(get_settings().database_path)
    yield


app = FastAPI(title="API", version="0.1.0", lifespan=lifespan)

app.include_router(auth_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
