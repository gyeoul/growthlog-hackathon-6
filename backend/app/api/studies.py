"""Study endpoints: create, list, detail, join, leave.

Reads are public; writes require the existing session cookie via `current_user`.
The owner is always a member (`create_study` inserts both rows), and the owner
cannot leave in this MVP.
"""

from fastapi import APIRouter, Depends, HTTPException

from app import db
from app.config import Settings, get_settings
from app.db import Member
from app.db import StudyRow
from app.deps import current_user, optional_user
from app.schemas import Study, StudyDetail, StudyIn, StudyList, StudyMember, StudyOwner

router = APIRouter(prefix="/api/studies", tags=["studies"])

NOT_FOUND = "스터디를 찾을 수 없습니다"

_AUTH_RESPONSES = {401: {"description": "로그인이 필요합니다"}}
_NOT_FOUND_RESPONSES = {404: {"description": NOT_FOUND}}


def _out(row: StudyRow) -> Study:
    return Study(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        capacity=row["capacity"],
        member_count=row["member_count"],
        owner=StudyOwner(id=row["owner_id"], name=row["owner_name"]),
        created_at=row["created_at"],
        is_open=row["member_count"] < row["capacity"],
    )


def _detail(path: str, row: StudyRow, user_id: int | None) -> StudyDetail:
    members = db.list_study_members(path, row["id"])
    return StudyDetail(
        **_out(row).model_dump(),
        members=[StudyMember(**m) for m in members],
        is_member=user_id is not None and any(m["user_id"] == user_id for m in members),
        is_owner=user_id is not None and row["owner_id"] == user_id,
    )


@router.get("", response_model=StudyList)
def list_studies(settings: Settings = Depends(get_settings)) -> StudyList:
    return StudyList(
        studies=[_out(r) for r in db.list_studies(settings.database_path)]
    )


@router.post(
    "",
    response_model=StudyDetail,
    status_code=201,
    responses=_AUTH_RESPONSES,
)
def create_study(
    body: StudyIn,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> StudyDetail:
    row = db.create_study(
        settings.database_path,
        owner_id=user["id"],
        title=body.title,
        description=body.description,
        capacity=body.capacity,
    )
    return _detail(settings.database_path, row, user["id"])


@router.get(
    "/{study_id}", response_model=StudyDetail, responses=_NOT_FOUND_RESPONSES
)
def get_study(
    study_id: int,
    user: Member | None = Depends(optional_user),
    settings: Settings = Depends(get_settings),
) -> StudyDetail:
    row = db.get_study(settings.database_path, study_id)
    if row is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return _detail(settings.database_path, row, user["id"] if user else None)


@router.post(
    "/{study_id}/join",
    response_model=StudyDetail,
    responses={
        **_AUTH_RESPONSES,
        **_NOT_FOUND_RESPONSES,
        409: {"description": "이미 참여했거나 모집 인원이 가득 찼습니다"},
    },
)
def join_study(
    study_id: int,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> StudyDetail:
    result = db.join_study(settings.database_path, study_id, user["id"])
    if result == "not_found":
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    if result == "already_member":
        raise HTTPException(status_code=409, detail="이미 참여한 스터디입니다")
    if result == "full":
        raise HTTPException(status_code=409, detail="모집 인원이 가득 찼습니다")
    row = db.get_study(settings.database_path, study_id)
    if row is None:  # deleted between join and read
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return _detail(settings.database_path, row, user["id"])


@router.delete(
    "/{study_id}/members/me",
    status_code=200,
    response_model=StudyDetail,
    responses={
        **_AUTH_RESPONSES,
        **_NOT_FOUND_RESPONSES,
        403: {"description": "스터디 생성자는 탈퇴할 수 없습니다"},
        409: {"description": "참여하지 않은 스터디입니다"},
    },
)
def leave_study(
    study_id: int,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> StudyDetail:
    result = db.leave_study(settings.database_path, study_id, user["id"])
    if result == "not_found":
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    if result == "owner":
        raise HTTPException(status_code=403, detail="스터디 생성자는 탈퇴할 수 없습니다")
    if result == "not_member":
        raise HTTPException(status_code=409, detail="참여하지 않은 스터디입니다")
    row = db.get_study(settings.database_path, study_id)
    if row is None:  # deleted between leave and read
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return _detail(settings.database_path, row, user["id"])
