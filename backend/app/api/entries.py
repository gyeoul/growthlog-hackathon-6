"""Growth-log entry endpoints. Every row is scoped to the logged-in member."""

from fastapi import APIRouter, Depends, HTTPException, Response

from app import db
from app.config import Settings, get_settings
from app.db import Entry as EntryRow
from app.db import Member
from app.deps import current_user
from app.schemas import Entry, EntryIn, EntryList

router = APIRouter(prefix="/api/entries", tags=["entries"])


def _out(row: EntryRow) -> Entry:
    return Entry(**row)


@router.get("", response_model=EntryList)
def list_entries(
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> EntryList:
    return EntryList(entries=[_out(r) for r in db.list_entries(settings.database_path, user["id"])])


@router.post("", response_model=Entry, status_code=201)
def create_entry(
    body: EntryIn,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> Entry:
    row = db.create_entry(settings.database_path, user["id"], body.title, body.content)
    return _out(row)


@router.get("/{entry_id}", response_model=Entry)
def get_entry(
    entry_id: int,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> Entry:
    row = db.get_entry(settings.database_path, user["id"], entry_id)
    if row is None:
        raise HTTPException(status_code=404, detail="기록을 찾을 수 없습니다")
    return _out(row)


@router.put("/{entry_id}", response_model=Entry)
def update_entry(
    entry_id: int,
    body: EntryIn,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> Entry:
    row = db.update_entry(
        settings.database_path, user["id"], entry_id, body.title, body.content
    )
    if row is None:
        raise HTTPException(status_code=404, detail="기록을 찾을 수 없습니다")
    return _out(row)


@router.delete("/{entry_id}", status_code=204)
def delete_entry(
    entry_id: int,
    user: Member = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> Response:
    if not db.delete_entry(settings.database_path, user["id"], entry_id):
        raise HTTPException(status_code=404, detail="기록을 찾을 수 없습니다")
    return Response(status_code=204)
