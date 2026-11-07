"""Persistence contract tests. No network, no Google."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import Settings, get_settings
from app.main import create_app
from app.security import SESSION_COOKIE, create_session


@pytest.fixture
def settings(tmp_path) -> Settings:
    settings = Settings(
        google_client_id="cid",
        google_client_secret="csecret",
        oauth_redirect_uri="http://testserver/api/auth/google/callback",
        session_secret="test-secret",
        session_ttl=3600,
        allowed_email_domain="knou.ac.kr",
        cookie_secure=False,
        database_path=str(tmp_path / "data" / "test.db"),
    )
    db.init_db(settings.database_path)
    yield settings


@pytest.fixture
def member(settings) -> db.Member:
    return db.upsert_member(
        settings.database_path,
        google_sub="sub-1",
        email="student@knou.ac.kr",
        name="김학생",
        picture=None,
    )


@pytest.fixture
def auth(member, settings) -> dict[str, str]:
    token = create_session(member["id"], settings.session_secret, 3600)
    return {"cookie": f"{SESSION_COOKIE}={token}"}


@pytest.fixture
def client(settings) -> TestClient:
    with TestClient(create_app(settings)) as c:
        yield c


def test_database_file_is_created_including_parent_dir(settings):
    assert settings.database_path.endswith("data/test.db")
    db.init_db(settings.database_path)
    from pathlib import Path

    assert Path(settings.database_path).is_file()


def test_entries_require_login(client):
    assert client.get("/api/entries").status_code == 401
    assert client.post("/api/entries", json={"title": "x"}).status_code == 401


def test_entry_roundtrip(client, auth):
    created = client.post(
        "/api/entries", json={"title": "첫 기록", "content": "오늘 배운 것"}, headers=auth
    )
    assert created.status_code == 201
    entry = created.json()
    assert entry["title"] == "첫 기록"
    assert entry["content"] == "오늘 배운 것"
    assert entry["created_at"] == entry["updated_at"]

    listed = client.get("/api/entries", headers=auth).json()["entries"]
    assert [e["id"] for e in listed] == [entry["id"]]

    updated = client.put(
        f"/api/entries/{entry['id']}",
        json={"title": "수정", "content": "내용 변경"},
        headers=auth,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "수정"
    assert updated.json()["updated_at"] >= entry["updated_at"]
    assert updated.json()["created_at"] == entry["created_at"]

    assert client.delete(f"/api/entries/{entry['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/entries/{entry['id']}", headers=auth).status_code == 404


def test_data_survives_a_new_connection_and_app_restart(settings, member):
    """The whole point of SQLite here: rows outlive the process."""
    db.create_entry(settings.database_path, member["id"], "영속성", "남아 있어야 함")

    # Simulate a restart: brand-new app object against the same file.
    from app.main import create_app

    with TestClient(create_app(settings)) as restarted:
        token = create_session(member["id"], settings.session_secret, 3600)
        res = restarted.get("/api/entries", headers={"cookie": f"{SESSION_COOKIE}={token}"})
        assert res.status_code == 200
        assert [e["title"] for e in res.json()["entries"]] == ["영속성"]


def test_migrations_are_idempotent_and_incremental(tmp_path):
    path = str(tmp_path / "m.db")

    db.init_db(path)
    db.init_db(path)  # second call must not re-run CREATE TABLE

    with db.session(path) as conn:
        versions = [r[0] for r in conn.execute("SELECT version FROM schema_version ORDER BY version")]
    assert versions == [1, 2]

    # An older database (v1 only) gains the new table without losing rows.
    old = str(tmp_path / "old.db")
    with sqlite3.connect(old) as conn:
        conn.executescript(db.MIGRATIONS[0].sql)
        conn.execute(
            "CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        conn.execute("INSERT INTO schema_version VALUES (1, '2024-01-01T00:00:00+00:00')")
        conn.execute(
            "INSERT INTO users (google_sub, email, name, picture, created_at, last_login_at)"
            " VALUES ('s','a@knou.ac.kr',NULL,NULL,'x','x')"
        )
    db.init_db(old)
    assert db.stats(old) == {"members": 1, "entries": 0}


def test_entries_are_scoped_to_their_owner(client, settings, auth, member):
    other = db.upsert_member(
        settings.database_path,
        google_sub="sub-2",
        email="other@knou.ac.kr",
        name=None,
        picture=None,
    )
    mine = db.create_entry(settings.database_path, member["id"], "내 기록", "")

    other_auth = {
        "cookie": f"{SESSION_COOKIE}={create_session(other['id'], settings.session_secret, 3600)}"
    }
    assert client.get("/api/entries", headers=other_auth).json() == {"entries": []}
    assert client.get(f"/api/entries/{mine['id']}", headers=other_auth).status_code == 404
    assert client.delete(f"/api/entries/{mine['id']}", headers=other_auth).status_code == 404
    # Still the owner's.
    assert client.get(f"/api/entries/{mine['id']}", headers=auth).status_code == 200


def test_validation_bounds(client, auth):
    assert client.post("/api/entries", json={"title": ""}, headers=auth).status_code == 422
    assert (
        client.post("/api/entries", json={"title": "x" * 201}, headers=auth).status_code
        == 422
    )
    assert (
        client.post(
            "/api/entries", json={"title": "ok", "content": "x" * 20_001}, headers=auth
        ).status_code
        == 422
    )


def test_newest_entries_come_first(client, auth, settings, member):
    for title in ["하나", "둘", "셋"]:
        db.create_entry(settings.database_path, member["id"], title, "")
    titles = [e["title"] for e in client.get("/api/entries", headers=auth).json()["entries"]]
    assert titles == ["셋", "둘", "하나"]


def test_stats_needs_login_and_counts_rows(client, auth, member, settings):
    assert client.get("/api/stats").status_code == 401
    db.create_entry(settings.database_path, member["id"], "a", "")
    db.create_entry(settings.database_path, member["id"], "b", "")
    assert client.get("/api/stats", headers=auth).json() == {"members": 1, "entries": 2}


def test_deleting_member_cascades_to_entries(settings, member):
    db.create_entry(settings.database_path, member["id"], "t", "")
    with db.session(settings.database_path) as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (member["id"],))
    assert db.stats(settings.database_path) == {"members": 0, "entries": 0}
