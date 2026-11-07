"""Study contract tests: lifecycle, membership rules, validation, auth."""

import concurrent.futures

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import Settings
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
    return settings


def _member(settings: Settings, sub: str, name: str) -> db.Member:
    return db.upsert_member(
        settings.database_path,
        google_sub=sub,
        email=f"{sub}@knou.ac.kr",
        name=name,
        picture=None,
    )


def _auth(settings: Settings, member: db.Member) -> dict[str, str]:
    token = create_session(member["id"], settings.session_secret, 3600)
    return {"cookie": f"{SESSION_COOKIE}={token}"}


@pytest.fixture
def owner(settings) -> db.Member:
    return _member(settings, "owner", "김소유")


@pytest.fixture
def guest(settings) -> db.Member:
    return _member(settings, "guest", "이참여")


@pytest.fixture
def owner_auth(settings, owner) -> dict[str, str]:
    return _auth(settings, owner)


@pytest.fixture
def guest_auth(settings, guest) -> dict[str, str]:
    return _auth(settings, guest)


@pytest.fixture
def client(settings) -> TestClient:
    with TestClient(create_app(settings)) as c:
        yield c


def _create(client, auth, **overrides):
    body = {"title": "알고리즘 스터디", "description": "주 1회 문제 풀이", "capacity": 3}
    body.update(overrides)
    return client.post("/api/studies", json=body, headers=auth)


# 1. creation


def test_create_study_returns_detail_and_owner_is_first_member(client, owner_auth, owner):
    res = _create(client, owner_auth)
    assert res.status_code == 201
    study = res.json()
    assert study["title"] == "알고리즘 스터디"
    assert study["description"] == "주 1회 문제 풀이"
    assert study["capacity"] == 3
    assert study["member_count"] == 1
    assert study["owner"] == {"id": owner["id"], "name": "김소유"}
    assert study["is_open"] is True
    assert study["is_member"] is True and study["is_owner"] is True
    assert [m["user_id"] for m in study["members"]] == [owner["id"]]
    assert study["created_at"]


# 2. owner auto-join is visible to another reader


def test_owner_membership_is_persisted(client, owner_auth, owner, guest_auth):
    study_id = _create(client, owner_auth).json()["id"]
    detail = client.get(f"/api/studies/{study_id}", headers=guest_auth).json()
    assert len(detail["members"]) == 1
    assert detail["members"][0]["user_id"] == owner["id"]
    assert detail["members"][0]["name"] == "김소유"
    assert detail["is_member"] is False
    assert detail["is_owner"] is False


# 3. list and detail


def test_list_is_public_and_newest_first(client, owner_auth):
    first = _create(client, owner_auth, title="첫째").json()["id"]
    second = _create(client, owner_auth, title="둘째").json()["id"]
    res = client.get("/api/studies")
    assert res.status_code == 200
    ids = [s["id"] for s in res.json()["studies"]]
    assert ids.index(second) < ids.index(first)

    detail = client.get(f"/api/studies/{first}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["title"] == "첫째"
    assert body["is_member"] is False and body["is_owner"] is False
    assert len(body["members"]) == 1


# 4. join


def test_join_updates_count_and_availability(client, owner_auth, guest_auth, settings):
    study_id = _create(client, owner_auth, capacity=2).json()["id"]
    res = client.post(f"/api/studies/{study_id}/join", headers=guest_auth)
    assert res.status_code == 200
    body = res.json()
    assert body["member_count"] == 2
    assert body["is_open"] is False
    assert body["is_member"] is True
    assert db.get_study(settings.database_path, study_id)["member_count"] == 2


# 5. duplicate join


def test_duplicate_join_is_conflict(client, owner_auth, guest_auth):
    study_id = _create(client, owner_auth).json()["id"]
    assert client.post(f"/api/studies/{study_id}/join", headers=guest_auth).status_code == 200
    assert client.post(f"/api/studies/{study_id}/join", headers=guest_auth).status_code == 409
    assert client.post(f"/api/studies/{study_id}/join", headers=owner_auth).status_code == 409


# 6. capacity


def test_full_study_rejects_join(client, owner_auth, guest_auth, settings):
    study_id = _create(client, owner_auth, capacity=2).json()["id"]
    client.post(f"/api/studies/{study_id}/join", headers=guest_auth)

    third = _member(settings, "third", "박셋째")
    res = client.post(
        f"/api/studies/{study_id}/join", headers=_auth(settings, third)
    )
    assert res.status_code == 409
    assert db.get_study(settings.database_path, study_id)["member_count"] == 2


def test_capacity_is_not_exceeded_under_concurrent_joins(settings, owner):
    study = db.create_study(
        settings.database_path,
        owner_id=owner["id"],
        title="동시성",
        description="정원 경쟁",
        capacity=2,
    )
    contenders = [_member(settings, f"c{i}", f"경쟁자{i}")["id"] for i in range(6)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(
            pool.map(
                lambda uid: db.join_study(settings.database_path, study["id"], uid),
                contenders,
            )
        )

    assert results.count("joined") == 1
    assert results.count("full") == 5
    assert db.get_study(settings.database_path, study["id"])["member_count"] == 2


# 7. leave


def test_member_can_leave_and_seat_reopens(client, owner_auth, guest_auth, settings):
    study_id = _create(client, owner_auth, capacity=2).json()["id"]
    client.post(f"/api/studies/{study_id}/join", headers=guest_auth)

    res = client.delete(f"/api/studies/{study_id}/members/me", headers=guest_auth)
    assert res.status_code == 200
    body = res.json()
    assert body["member_count"] == 1
    assert body["is_open"] is True
    assert body["is_member"] is False

    third = _member(settings, "late", "최늦둥")
    assert (
        client.post(f"/api/studies/{study_id}/join", headers=_auth(settings, third)).status_code
        == 200
    )

    # Leaving twice is a state conflict, not a crash.
    assert (
        client.delete(f"/api/studies/{study_id}/members/me", headers=guest_auth).status_code
        == 409
    )


# 8. owner cannot leave


def test_owner_cannot_leave(client, owner_auth, settings):
    study_id = _create(client, owner_auth).json()["id"]
    res = client.delete(f"/api/studies/{study_id}/members/me", headers=owner_auth)
    assert res.status_code == 403
    assert db.get_study(settings.database_path, study_id)["member_count"] == 1


# 9. missing study


def test_unknown_study_is_404(client, owner_auth, guest_auth):
    assert client.get("/api/studies/999").status_code == 404
    assert client.post("/api/studies/999/join", headers=guest_auth).status_code == 404
    assert client.delete("/api/studies/999/members/me", headers=guest_auth).status_code == 404


# 10. authentication


def test_writes_require_login(client, owner_auth):
    assert (
        client.post(
            "/api/studies",
            json={"title": "x", "description": "y", "capacity": 2},
        ).status_code
        == 401
    )
    study_id = _create(client, owner_auth).json()["id"]
    assert client.post(f"/api/studies/{study_id}/join").status_code == 401
    assert client.delete(f"/api/studies/{study_id}/members/me").status_code == 401
    # Forged client-supplied identity is not a thing: body/query ids are ignored.
    assert (
        client.post(f"/api/studies/{study_id}/join", json={"user_id": 1}).status_code == 401
    )


# validation


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 101},
        {"description": ""},
        {"description": " "},
        {"description": "x" * 2001},
        {"capacity": 1},
        {"capacity": 101},
    ],
)
def test_invalid_study_payload_is_422(client, owner_auth, overrides):
    assert _create(client, owner_auth, **overrides).status_code == 422


def test_titles_are_trimmed(client, owner_auth):
    body = _create(client, owner_auth, title="  공백 정리  ").json()
    assert body["title"] == "공백 정리"
