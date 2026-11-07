"""Request/response models for the auth endpoints."""

from pydantic import BaseModel


class User(BaseModel):
    id: int
    email: str
    name: str | None
    picture: str | None
    created_at: str
    last_login_at: str


class SessionState(BaseModel):
    user: User | None
