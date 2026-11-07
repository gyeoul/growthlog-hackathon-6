"""Auth contract tests. Google's network calls are monkeypatched."""

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import Settings, get_settings
from app.main import create_app
from app.security import SESSION_COOKIE, create_session, read_session
from app.services import google

DOMAIN = "knou.ac.kr"


@pytest.fixture
def settings(tmp_path) -> Settings:
    settings = Settings(
        google_client_id="cid",
        google_client_secret="csecret",
        oauth_redirect_uri="http://testserver/api/auth/google/callback",
        session_secret="test-secret",
        session_ttl=3600,
        allowed_email_domain=DOMAIN,
        cookie_secure=False,
        database_path=str(tmp_path / "test.db"),
    )
    yield settings


@pytest.fixture
def client(settings) -> TestClient:
    # Each test gets its own app pinned to its own database file.
    with TestClient(create_app(settings)) as c:
        yield c


def profile(email: str, verified: bool = True, sub: str = "g-1") -> google.GoogleProfile:
    return google.GoogleProfile(
        sub=sub, email=email, email_verified=verified, name="홍길동", picture=None
    )


def login(client: TestClient, monkeypatch, prof: google.GoogleProfile):
    monkeypatch.setattr(google, "fetch_profile", lambda settings, code: prof)
    start = client.get("/api/auth/google/login", follow_redirects=False)
    state = start.cookies["oauth_state"]
    return client.get(
        "/api/auth/google/callback",
        params={"code": "abc", "state": state},
        follow_redirects=False,
    )


def test_login_redirects_to_google_with_state(client, settings):
    res = client.get("/api/auth/google/login", follow_redirects=False)
    assert res.status_code == 307
    location = res.headers["location"]
    assert location.startswith(settings.google_authorize_url)
    assert "client_id=cid" in location
    assert "state=" in location
    assert res.cookies["oauth_state"]


def test_login_redirects_with_error_when_google_not_configured(settings):
    unconfigured = create_app(
        Settings(**{**settings.__dict__, "google_client_id": "", "google_client_secret": ""})
    )
    with TestClient(unconfigured) as client:
        res = client.get("/api/auth/google/login", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == (
        "/?auth_error=config&missing=GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET"
    )
    assert SESSION_COOKIE not in res.cookies


def test_member_domain_creates_member_and_session(client, monkeypatch):
    res = login(client, monkeypatch, profile("student@knou.ac.kr"))
    assert res.status_code == 303
    assert res.headers["location"] == "/"
    assert SESSION_COOKIE in res.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "student@knou.ac.kr"
    assert me.json()["name"] == "홍길동"


def test_domain_check_ignores_case_and_whitespace(client, monkeypatch):
    res = login(client, monkeypatch, profile("  Student@KNOU.AC.KR "))
    assert res.status_code == 303
    assert client.get("/api/auth/me").json()["email"] == "student@knou.ac.kr"


@pytest.mark.parametrize(
    "email",
    [
        "student@gmail.com",
        "student@knou.ac.kr.evil.com",  # suffix spoofing must fail
        "knou.ac.kr@gmail.com",
        "student@sub.knou.ac.kr",
    ],
)
def test_non_member_domain_is_rejected(client, monkeypatch, email):
    res = login(client, monkeypatch, profile(email))
    assert res.status_code == 303
    assert res.headers["location"] == "/?auth_error=domain"
    assert SESSION_COOKIE not in res.cookies
    assert client.get("/api/auth/me").status_code == 401


def test_unverified_email_is_rejected(client, monkeypatch):
    res = login(client, monkeypatch, profile("student@knou.ac.kr", verified=False))
    assert res.headers["location"] == "/?auth_error=domain"
    assert client.get("/api/auth/me").status_code == 401


def test_state_mismatch_is_rejected(client, monkeypatch):
    monkeypatch.setattr(google, "fetch_profile", lambda settings, code: profile("s@knou.ac.kr"))
    client.get("/api/auth/google/login", follow_redirects=False)
    res = client.get(
        "/api/auth/google/callback",
        params={"code": "abc", "state": "forged"},
        follow_redirects=False,
    )
    assert res.headers["location"] == "/?auth_error=state"
    assert client.get("/api/auth/me").status_code == 401


def test_google_failure_redirects_with_error(client, monkeypatch):
    def boom(settings, code):
        raise google.GoogleAuthError("nope")

    monkeypatch.setattr(google, "fetch_profile", boom)
    start = client.get("/api/auth/google/login", follow_redirects=False)
    res = client.get(
        "/api/auth/google/callback",
        params={"code": "abc", "state": start.cookies["oauth_state"]},
        follow_redirects=False,
    )
    assert res.headers["location"] == "/?auth_error=google"


def test_repeat_login_reuses_member(client, monkeypatch):
    login(client, monkeypatch, profile("student@knou.ac.kr"))
    first = client.get("/api/auth/me").json()
    client.cookies.clear()
    login(client, monkeypatch, profile("student@knou.ac.kr", sub="g-1"))
    second = client.get("/api/auth/me").json()
    assert first["id"] == second["id"]
    assert first["created_at"] == second["created_at"]


def test_session_endpoint_returns_null_when_anonymous(client):
    assert client.get("/api/auth/session").json() == {"user": None}


def test_logout_clears_session(client, monkeypatch):
    login(client, monkeypatch, profile("student@knou.ac.kr"))
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/session").json() == {"user": None}
    assert client.get("/api/auth/me").status_code == 401


def test_tampered_and_expired_sessions_are_rejected(client, monkeypatch):
    login(client, monkeypatch, profile("student@knou.ac.kr"))
    good = client.cookies[SESSION_COOKIE]

    def with_header(token: str):
        return client.get("/api/auth/me", headers={"cookie": f"{SESSION_COOKIE}={token}"})

    assert with_header(good).status_code == 200
    assert with_header(good[:-2] + "xx").status_code == 401
    assert with_header(create_session(1, "test-secret", ttl=-10)).status_code == 401
    assert with_header(create_session(1, "wrong-secret", ttl=600)).status_code == 401
    assert read_session("garbage", "test-secret") is None
