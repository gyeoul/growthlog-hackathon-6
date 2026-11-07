"""Request/response models."""

from pydantic import BaseModel, Field


class User(BaseModel):
    id: int
    email: str
    name: str | None
    picture: str | None
    created_at: str
    last_login_at: str


class SessionState(BaseModel):
    user: User | None


class EntryIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default="", max_length=20_000)


class Entry(BaseModel):
    id: int
    title: str
    content: str
    created_at: str
    updated_at: str


class EntryList(BaseModel):
    entries: list[Entry]
