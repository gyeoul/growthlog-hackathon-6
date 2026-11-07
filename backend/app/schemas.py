"""Request/response models."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


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


# --- studies -------------------------------------------------------------

# `str_strip_whitespace` makes "   " fail min_length, so titles are non-blank.
StudyTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
StudyDescription = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class StudyIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: StudyTitle
    description: StudyDescription
    capacity: int = Field(ge=2, le=100)


class StudyOwner(BaseModel):
    id: int
    name: str


class Study(BaseModel):
    id: int
    title: str
    description: str
    capacity: int
    member_count: int
    owner: StudyOwner
    created_at: str
    is_open: bool


class StudyList(BaseModel):
    studies: list[Study]


class StudyMember(BaseModel):
    user_id: int
    name: str
    joined_at: str


class StudyDetail(Study):
    members: list[StudyMember]
    is_member: bool
    is_owner: bool
