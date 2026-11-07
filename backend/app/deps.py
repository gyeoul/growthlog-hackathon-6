"""Session-backed current user lookup."""

from fastapi import Cookie, Depends, HTTPException

from app import db
from app.config import Settings, get_settings
from app.db import Member
from app.security import SESSION_COOKIE, read_session


def _member_from_session(session: str | None, settings: Settings) -> Member | None:
    if not session:
        return None
    user_id = read_session(session, settings.session_secret)
    if user_id is None:
        return None
    return db.get_member(settings.database_path, user_id)


def optional_user(
    session: str | None = Cookie(default=None),
    settings: Settings = Depends(get_settings),
) -> Member | None:
    """The session member, or None. For endpoints that also serve anonymous users."""
    return _member_from_session(session, settings)


def current_user(
    session: str | None = Cookie(default=None),
    settings: Settings = Depends(get_settings),
) -> Member:
    if not session:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    user_id = read_session(session, settings.session_secret)
    if user_id is None:
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다")
    member = db.get_member(settings.database_path, user_id)
    if member is None:
        raise HTTPException(status_code=401, detail="회원 정보를 찾을 수 없습니다")
    return member
