import logging
import os
import secrets
from dataclasses import dataclass

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_warned_ephemeral_secret = False

# Real environment variables win: load_dotenv does not override them.
load_dotenv()


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    google_client_id: str
    google_client_secret: str
    oauth_redirect_uri: str
    session_secret: str
    session_ttl: int
    allowed_email_domain: str
    cookie_secure: bool
    database_path: str
    google_authorize_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    google_token_url: str = "https://oauth2.googleapis.com/token"
    google_userinfo_url: str = "https://openidconnect.googleapis.com/v1/userinfo"

    @property
    def google_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)


def get_settings() -> Settings:
    global _warned_ephemeral_secret
    secret = os.getenv("SESSION_SECRET", "")
    if not secret:
        # Dev convenience: sessions simply die on restart. Set SESSION_SECRET in production.
        if not _warned_ephemeral_secret:
            logger.warning(
                "SESSION_SECRET is unset; using a random per-process secret. "
                "Sessions will not survive a restart."
            )
            _warned_ephemeral_secret = True
        secret = secrets.token_urlsafe(32)

    return Settings(
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        oauth_redirect_uri=os.getenv(
            "OAUTH_REDIRECT_URI", "http://localhost:3000/api/auth/google/callback"
        ),
        session_secret=secret,
        session_ttl=int(os.getenv("SESSION_TTL", "604800")),
        allowed_email_domain=os.getenv("ALLOWED_EMAIL_DOMAIN", "knou.ac.kr").strip().lower(),
        cookie_secure=_flag("COOKIE_SECURE"),
        database_path=os.getenv("DATABASE_PATH", "app.db"),
        # Overridable so the full login flow can be exercised against a fake IdP.
        google_authorize_url=os.getenv(
            "GOOGLE_AUTHORIZE_URL", "https://accounts.google.com/o/oauth2/v2/auth"
        ),
        google_token_url=os.getenv(
            "GOOGLE_TOKEN_URL", "https://oauth2.googleapis.com/token"
        ),
        google_userinfo_url=os.getenv(
            "GOOGLE_USERINFO_URL", "https://openidconnect.googleapis.com/v1/userinfo"
        ),
    )
