"""Google OAuth 2.0 code exchange and profile lookup (stdlib HTTP, no deps)."""

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app.config import Settings

TIMEOUT = 10.0


class GoogleAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class GoogleProfile:
    sub: str
    email: str
    email_verified: bool
    name: str | None
    picture: str | None


def _request(url: str, *, data: bytes | None = None, headers: dict[str, str]) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:300]
        raise GoogleAuthError(f"Google returned {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise GoogleAuthError(f"Google request failed: {exc}") from exc


def authorize_url(settings: Settings, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.oauth_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    return f"{settings.google_authorize_url}?{query}"


def fetch_profile(settings: Settings, code: str) -> GoogleProfile:
    token = _request(
        settings.google_token_url,
        data=urllib.parse.urlencode(
            {
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.oauth_redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    access_token = token.get("access_token")
    if not access_token:
        raise GoogleAuthError("Token response contained no access_token")

    info = _request(
        settings.google_userinfo_url, headers={"Authorization": f"Bearer {access_token}"}
    )
    try:
        return GoogleProfile(
            sub=info["sub"],
            email=info["email"],
            # The userinfo endpoint returns a bool here, unlike the string JWT claim.
            email_verified=bool(info.get("email_verified")),
            name=info.get("name"),
            picture=info.get("picture"),
        )
    except KeyError as exc:
        raise GoogleAuthError(f"Profile response missing {exc}") from exc
