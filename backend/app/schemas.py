"""Request/response models."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


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


# --- semester planner ----------------------------------------------------

TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


class SemesterIn(BaseModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def _ordered(self) -> "SemesterIn":
        if self.end_date < self.start_date:
            raise ValueError("학기 종료일은 시작일 이후여야 합니다")
        return self


class Semester(BaseModel):
    start_date: str
    end_date: str


class SemesterState(BaseModel):
    semester: Semester | None


class CourseIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    credits: int = Field(default=3, ge=1, le=6)
    total_lectures: int = Field(default=15, ge=1, le=30)
    done_lectures: int = Field(default=0, ge=0, le=30)
    minutes_per_lecture: int = Field(default=50, ge=10, le=240)

    @model_validator(mode="after")
    def _within_total(self) -> "CourseIn":
        if self.done_lectures > self.total_lectures:
            raise ValueError("들은 강의 수가 전체 강의 수보다 많습니다")
        return self


class Course(BaseModel):
    id: int
    name: str
    credits: int
    total_lectures: int
    done_lectures: int
    minutes_per_lecture: int


class CourseList(BaseModel):
    courses: list[Course]


class DeadlineIn(BaseModel):
    course_id: int
    kind: Literal["assignment", "attendance", "exam"]
    title: str = Field(default="", max_length=100)
    due_date: date


class Deadline(BaseModel):
    id: int
    course_id: int
    kind: str
    title: str
    due_date: str


class DeadlineList(BaseModel):
    deadlines: list[Deadline]


class Slot(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0 = Monday")
    start_time: str = Field(pattern=TIME_PATTERN)
    end_time: str = Field(pattern=TIME_PATTERN)

    @model_validator(mode="after")
    def _ordered(self) -> "Slot":
        if self.end_time <= self.start_time:
            raise ValueError("종료 시간은 시작 시간 이후여야 합니다")
        return self


class Availability(BaseModel):
    slots: list[Slot] = Field(max_length=50)


class PlanBlock(BaseModel):
    id: int
    course_id: int
    deadline_id: int | None
    kind: str
    title: str
    date: str
    start_time: str
    end_time: str
    done: bool


class PlanBlockList(BaseModel):
    blocks: list[PlanBlock]


class BlockDoneIn(BaseModel):
    done: bool


class GenerateIn(BaseModel):
    """The browser's local date/time, so "today" means the member's today."""

    today: date | None = None
    now: str | None = Field(default=None, pattern=TIME_PATTERN)


class GenerateResult(BaseModel):
    scheduled: int
    unscheduled: list[str]

