"""Semester planner endpoints. Every row is scoped to the logged-in member."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app import db
from app.config import Settings, get_settings
from app.db import Member
from app.deps import current_user
from app.schemas import (
    Availability,
    BlockDoneIn,
    Course,
    CourseIn,
    CourseList,
    Deadline,
    DeadlineIn,
    DeadlineList,
    GenerateIn,
    GenerateResult,
    PlanBlock,
    PlanBlockList,
    Semester,
    SemesterIn,
    SemesterState,
    Slot,
)
from app.services import planner

router = APIRouter(prefix="/api", tags=["planner"])

DEFAULT_DEADLINE_TITLES = {"assignment": "과제물", "attendance": "출석수업", "exam": "기말시험"}


@router.get("/semester", response_model=SemesterState)
def get_semester(
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> SemesterState:
    row = db.get_semester(settings.database_path, user["id"])
    return SemesterState(semester=Semester(**row) if row else None)


@router.put("/semester", response_model=Semester)
def put_semester(
    body: SemesterIn,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> Semester:
    row = db.set_semester(
        settings.database_path,
        user["id"],
        body.start_date.isoformat(),
        body.end_date.isoformat(),
    )
    return Semester(**row)


@router.get("/courses", response_model=CourseList)
def list_courses(
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> CourseList:
    rows = db.list_courses(settings.database_path, user["id"])
    return CourseList(courses=[Course(**r) for r in rows])


@router.post("/courses", response_model=Course, status_code=201)
def create_course(
    body: CourseIn,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> Course:
    row = db.create_course(settings.database_path, user["id"], **body.model_dump())
    return Course(**row)


@router.put("/courses/{course_id}", response_model=Course)
def update_course(
    course_id: int,
    body: CourseIn,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> Course:
    row = db.update_course(settings.database_path, user["id"], course_id, **body.model_dump())
    if row is None:
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다")
    return Course(**row)


@router.delete("/courses/{course_id}", status_code=204)
def delete_course(
    course_id: int,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> Response:
    if not db.delete_course(settings.database_path, user["id"], course_id):
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다")
    return Response(status_code=204)


@router.get("/deadlines", response_model=DeadlineList)
def list_deadlines(
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> DeadlineList:
    rows = db.list_deadlines(settings.database_path, user["id"])
    return DeadlineList(deadlines=[Deadline(**r) for r in rows])


@router.post("/deadlines", response_model=Deadline, status_code=201)
def create_deadline(
    body: DeadlineIn,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> Deadline:
    # A member may only attach deadlines to their own courses.
    if db.get_course(settings.database_path, user["id"], body.course_id) is None:
        raise HTTPException(status_code=404, detail="강의를 찾을 수 없습니다")
    row = db.create_deadline(
        settings.database_path,
        user["id"],
        course_id=body.course_id,
        kind=body.kind,
        title=body.title.strip() or DEFAULT_DEADLINE_TITLES[body.kind],
        due_date=body.due_date.isoformat(),
    )
    return Deadline(**row)


@router.delete("/deadlines/{deadline_id}", status_code=204)
def delete_deadline(
    deadline_id: int,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> Response:
    if not db.delete_deadline(settings.database_path, user["id"], deadline_id):
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다")
    return Response(status_code=204)


@router.get("/availability", response_model=Availability)
def get_availability(
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> Availability:
    rows = db.list_availability(settings.database_path, user["id"])
    return Availability(slots=[Slot(**r) for r in rows])


@router.put("/availability", response_model=Availability)
def put_availability(
    body: Availability,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> Availability:
    rows = db.replace_availability(
        settings.database_path, user["id"], [s.model_dump() for s in body.slots]
    )
    return Availability(slots=[Slot(**r) for r in rows])


@router.get("/plan", response_model=PlanBlockList)
def list_plan(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> PlanBlockList:
    rows = db.list_blocks(
        settings.database_path,
        user["id"],
        start.isoformat() if start else None,
        end.isoformat() if end else None,
    )
    return PlanBlockList(blocks=[PlanBlock(**r) for r in rows])


@router.post("/plan/generate", response_model=GenerateResult)
def generate_plan(
    body: GenerateIn,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> GenerateResult:
    """(Re)build the plan from today on. Finished and past blocks are kept."""
    path = settings.database_path
    semester = db.get_semester(path, user["id"])
    if semester is None:
        raise HTTPException(status_code=409, detail="먼저 학기 기간을 저장해 주세요")
    availability = db.list_availability(path, user["id"])
    if not availability:
        raise HTTPException(status_code=409, detail="먼저 공부 가능한 시간을 저장해 주세요")

    today = body.today or date.today()
    end = date.fromisoformat(semester["end_date"])
    if end < today:
        raise HTTPException(status_code=409, detail="학기가 이미 끝났습니다")
    today = max(today, date.fromisoformat(semester["start_date"]))

    blocks = db.list_blocks(path, user["id"])
    tasks = planner.build_tasks(
        today,
        end,
        db.list_courses(path, user["id"]),
        db.list_deadlines(path, user["id"]),
        [b for b in blocks if b["done"]],
    )
    # Unfinished blocks from today on are about to be replaced, so they do not
    # count as occupied time.
    kept = [b for b in blocks if b["done"] or b["date"] < today.isoformat()]
    now_minutes = 0
    if body.now and body.today == today:
        now_minutes = planner.to_minutes(body.now)
    placed, unplaced = planner.schedule(today, end, tasks, availability, kept, now_minutes)

    db.replace_open_blocks(path, user["id"], today.isoformat(), placed)
    return GenerateResult(scheduled=len(placed), unscheduled=[t.title for t in unplaced])


@router.patch("/plan/blocks/{block_id}", response_model=PlanBlock)
def set_block_done(
    block_id: int,
    body: BlockDoneIn,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> PlanBlock:
    row = db.set_block_done(settings.database_path, user["id"], block_id, body.done)
    if row is None:
        raise HTTPException(status_code=404, detail="계획을 찾을 수 없습니다")
    return PlanBlock(**row)
