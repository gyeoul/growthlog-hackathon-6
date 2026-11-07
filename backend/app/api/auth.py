"""Google login. Membership is restricted to one email domain.

The domain check runs on the server after the token exchange, so a client can
never promote itself to a member by editing a request.
"""

import logging

from fastapi import APIRouter, Cookie, Depends, Query, Response
from fastapi.responses import RedirectResponse

from app import db
from app.config import Settings, get_settings
from app.deps import current_user
from app.schemas import SessionState, User
from app.security import SESSION_COOKIE, create_session, new_state, read_session
from app.services import google

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

STATE_COOKIE = "oauth_state"
STATE_TTL = 600  # 10 minutes


def _cookie(settings: Settings) -> dict:
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.cookie_secure,
        "path": "/",
    }


@router.get("/google/login")
def google_login(settings: Settings = Depends(get_settings)) -> RedirectResponse:
    if not settings.google_configured:
        # This endpoint is only ever opened by a browser, so explain it in the UI
        # instead of rendering a raw JSON error page.
        logger.error("Login attempted without GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET")
        return RedirectResponse("/?auth_error=config", status_code=303)
    state = new_state()
    res = RedirectResponse(google.authorize_url(settings, state))
    res.set_cookie(STATE_COOKIE, state, max_age=STATE_TTL, **_cookie(settings))
    return res


@router.get("/google/callback")
def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    oauth_state: str | None = Cookie(default=None),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    # CSRF: the state minted at /login must come back on the same browser.
    if not oauth_state or state != oauth_state:
        logger.warning("OAuth state mismatch")
        return RedirectResponse("/?auth_error=state", status_code=303)

    try:
        profile = google.fetch_profile(settings, code)
    except google.GoogleAuthError as exc:
        logger.warning("Google login failed: %s", exc)
        return RedirectResponse("/?auth_error=google", status_code=303)

    email = profile.email.strip().lower()
    domain = settings.allowed_email_domain
    if not profile.email_verified or not email.endswith(f"@{domain}"):
        logger.info("Rejected login for non-member email domain")
        return RedirectResponse("/?auth_error=domain", status_code=303)

    member = db.upsert_member(
        settings.database_path,
        google_sub=profile.sub,
        email=email,
        name=profile.name,
        picture=profile.picture,
    )

    res = RedirectResponse("/", status_code=303)
    res.set_cookie(
        SESSION_COOKIE,
        create_session(member["id"], settings.session_secret, settings.session_ttl),
        max_age=settings.session_ttl,
        **_cookie(settings),
    )
    res.delete_cookie(STATE_COOKIE, path="/")
    return res


@router.get("/session", response_model=SessionState)
def session_state(
    session: str | None = Cookie(default=None),
    settings: Settings = Depends(get_settings),
) -> SessionState:
    """Never 401s: the UI asks who is logged in before deciding what to render."""
    user_id = read_session(session, settings.session_secret) if session else None
    member = db.get_member(settings.database_path, user_id) if user_id else None
    return SessionState(user=User(**member) if member else None)


@router.post("/logout", status_code=204)
def logout() -> Response:
    res = Response(status_code=204)
    res.delete_cookie(SESSION_COOKIE, path="/")
    return res


@router.get("/me", response_model=User)
def me(user: User = Depends(current_user)) -> User:
    """Protected-route example: wire real features to this dependency."""
    return User(**user)
