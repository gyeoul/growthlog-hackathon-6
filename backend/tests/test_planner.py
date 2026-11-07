"""Semester planner: scheduling rules and the API contract. No network."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import Settings
from app.main import create_app
from app.security import SESSION_COOKIE, create_session
from app.services import planner

MON = date(2026, 11, 9)  # a Monday


def course(id: int, name: str, total: int = 3, done: int = 0, credits: int = 1) -> db.Course:
    return {
        "id": id,
        "name": name,
        "credits": credits,
        "total_lectures": total,
        "done_lectures": done,
        "minutes_per_lecture": 50,
    }


def evenings(*weekdays: int, start: str = "20:00", end: str = "22:00") -> list[db.Slot]:
    return [{"weekday": d, "start_time": start, "end_time": end} for d in weekdays]


# --- pure planner ---------------------------------------------------------


def test_lectures_fill_free_time_in_order():
    tasks = planner.build_tasks(MON, date(2026, 11, 30), [course(1, "통계")], [], [])
    assert [t.title for t in tasks] == ["통계 1강", "통계 2강", "통계 3강"]

    placed, unplaced = planner.schedule(MON, date(2026, 11, 30), tasks, evenings(0), [])
    assert unplaced == []
    assert [(b["date"], b["start_time"], b["end_time"]) for b in placed] == [
        ("2026-11-09", "20:00", "20:50"),
        ("2026-11-09", "20:50", "21:40"),
        ("2026-11-16", "20:00", "20:50"),
    ]


def test_already_finished_lectures_are_not_planned_again():
    done_block = {
        "id": 1, "course_id": 1, "deadline_id": None, "kind": "lecture", "title": "",
        "date": "2026-11-01", "start_time": "20:00", "end_time": "20:50", "done": True,
    }  # fmt: skip
    tasks = planner.build_tasks(
        MON, date(2026, 11, 30), [course(1, "통계", total=5, done=2)], [], [done_block]
    )
    assert [t.title for t in tasks] == ["통계 4강", "통계 5강"]


def test_same_course_is_not_stacked_when_another_is_as_urgent():
    tasks = planner.build_tasks(
        MON, date(2026, 11, 30), [course(1, "통계"), course(2, "경영")], [], []
    )
    placed, _ = planner.schedule(MON, date(2026, 11, 30), tasks, evenings(0, end="23:00"), [])
    first_evening = [b["course_id"] for b in placed if b["date"] == "2026-11-09"]
    assert first_evening == [1, 2, 1]


def test_exam_review_lands_in_the_two_weeks_before_the_exam():
    exam = {"id": 7, "course_id": 1, "kind": "exam", "title": "기말", "due_date": "2026-12-12"}
    tasks = planner.build_tasks(
        MON, date(2026, 12, 20), [course(1, "통계", total=1)], [exam], []
    )
    reviews = [t for t in tasks if t.kind == "review"]
    assert len(reviews) == 2  # 1 credit × 2 sessions
    assert all(t.first_day == date(2026, 11, 28) for t in reviews)
    assert all(t.last_day == date(2026, 12, 11) for t in reviews)
    # Lectures are due a week before the exam.
    assert [t.last_day for t in tasks if t.kind == "lecture"] == [date(2026, 12, 5)]

    placed, unplaced = planner.schedule(
        MON, date(2026, 12, 20), tasks, evenings(*range(7)), []
    )
    assert unplaced == []
    review_days = [b["date"] for b in placed if b["kind"] == "review"]
    assert review_days and all("2026-11-28" <= d <= "2026-12-11" for d in review_days)


def test_work_that_cannot_fit_before_its_deadline_is_reported():
    assignment = {
        "id": 3, "course_id": 1, "kind": "assignment", "title": "과제", "due_date": "2026-11-11",
    }  # fmt: skip
    tasks = planner.build_tasks(MON, date(2026, 11, 30), [course(1, "통계", total=1)], [assignment], [])
    # Only Monday 20:00–21:00 is free: room for one 60-minute session before the 11th.
    placed, unplaced = planner.schedule(
        MON, date(2026, 11, 30), tasks, evenings(0, end="21:00"), []
    )
    assert [b["title"] for b in placed if b["kind"] == "assignment"] == ["통계 과제 준비 (1/3)"]
    assert [t.title for t in unplaced] == ["통계 과제 준비 (2/3)", "통계 과제 준비 (3/3)"]


def test_kept_blocks_and_current_time_are_respected():
    kept = [{
        "id": 1, "course_id": 9, "deadline_id": None, "kind": "lecture", "title": "",
        "date": "2026-11-09", "start_time": "21:00", "end_time": "21:50", "done": True,
    }]  # fmt: skip
    tasks = planner.build_tasks(MON, date(2026, 11, 9), [course(1, "통계", total=2)], [], [])
    placed, unplaced = planner.schedule(
        MON, date(2026, 11, 9), tasks, evenings(0, start="19:00", end="23:00"), kept,
        now_minutes=planner.to_minutes("19:30"),
    )
    assert [(b["start_time"], b["end_time"]) for b in placed] == [
        ("19:30", "20:20"),
        ("21:50", "22:40"),
    ]
    assert unplaced == []


# --- API --------------------------------------------------------------------


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
        database_path=str(tmp_path / "planner.db"),
    )
    db.init_db(settings.database_path)
    return settings


def _auth(settings: Settings, sub: str) -> dict[str, str]:
    member = db.upsert_member(
        settings.database_path, google_sub=sub, email=f"{sub}@knou.ac.kr", name=None, picture=None
    )
    token = create_session(member["id"], settings.session_secret, 3600)
    return {"cookie": f"{SESSION_COOKIE}={token}"}


@pytest.fixture
def client(settings) -> TestClient:
    with TestClient(create_app(settings)) as c:
        yield c


def test_planner_requires_login(client):
    for path in ["/api/semester", "/api/courses", "/api/deadlines", "/api/availability", "/api/plan"]:
        assert client.get(path).status_code == 401
    assert client.post("/api/plan/generate", json={}).status_code == 401


def test_generate_needs_semester_and_free_time(client, settings):
    auth = _auth(settings, "a")
    res = client.post("/api/plan/generate", json={"today": "2026-11-09"}, headers=auth)
    assert res.status_code == 409
    client.put(
        "/api/semester", json={"start_date": "2026-09-01", "end_date": "2026-12-20"}, headers=auth
    )
    res = client.post("/api/plan/generate", json={"today": "2026-11-09"}, headers=auth)
    assert res.status_code == 409
    assert "공부 가능한 시간" in res.json()["detail"]


def test_full_flow_generate_check_and_regenerate(client, settings):
    auth = _auth(settings, "a")
    client.put(
        "/api/semester", json={"start_date": "2026-09-01", "end_date": "2026-12-20"}, headers=auth
    )
    stats = client.post(
        "/api/courses", json={"name": "통계", "total_lectures": 4, "done_lectures": 1}, headers=auth
    ).json()
    deadline = client.post(
        "/api/deadlines",
        json={"course_id": stats["id"], "kind": "assignment", "due_date": "2026-11-20"},
        headers=auth,
    )
    assert deadline.status_code == 201
    assert deadline.json()["title"] == "과제물"
    client.put(
        "/api/availability",
        json={"slots": [{"weekday": 0, "start_time": "20:00", "end_time": "22:00"}]},
        headers=auth,
    )

    res = client.post("/api/plan/generate", json={"today": "2026-11-09"}, headers=auth)
    assert res.status_code == 200
    assert res.json() == {"scheduled": 6, "unscheduled": []}  # 3 lectures + 3 assignment sessions

    blocks = client.get(
        "/api/plan", params={"start": "2026-11-09", "end": "2026-11-15"}, headers=auth
    ).json()["blocks"]
    assert [b["title"] for b in blocks] == ["통계 과제 준비 (1/3)", "통계 과제 준비 (2/3)"]

    first = blocks[0]
    done = client.patch(f"/api/plan/blocks/{first['id']}", json={"done": True}, headers=auth)
    assert done.json()["done"] is True

    # Regenerating keeps the finished block and only re-plans what is left.
    res = client.post("/api/plan/generate", json={"today": "2026-11-09"}, headers=auth)
    assert res.json() == {"scheduled": 5, "unscheduled": []}
    all_blocks = client.get("/api/plan", headers=auth).json()["blocks"]
    assert sum(b["done"] for b in all_blocks) == 1
    assert len(all_blocks) == 6

    # Deleting a course removes its deadlines and blocks with it.
    assert client.delete(f"/api/courses/{stats['id']}", headers=auth).status_code == 204
    assert client.get("/api/plan", headers=auth).json() == {"blocks": []}
    assert client.get("/api/deadlines", headers=auth).json() == {"deadlines": []}


def test_planner_rows_are_scoped_to_their_owner(client, settings):
    mine, other = _auth(settings, "a"), _auth(settings, "b")
    course_id = client.post("/api/courses", json={"name": "통계"}, headers=mine).json()["id"]

    assert client.get("/api/courses", headers=other).json() == {"courses": []}
    assert client.delete(f"/api/courses/{course_id}", headers=other).status_code == 404
    # Cannot hang a deadline on someone else's course.
    res = client.post(
        "/api/deadlines",
        json={"course_id": course_id, "kind": "exam", "due_date": "2026-12-12"},
        headers=other,
    )
    assert res.status_code == 404


def test_validation_bounds(client, settings):
    auth = _auth(settings, "a")
    bad_semester = {"start_date": "2026-12-20", "end_date": "2026-09-01"}
    assert client.put("/api/semester", json=bad_semester, headers=auth).status_code == 422
    too_many_done = {"name": "x", "total_lectures": 3, "done_lectures": 4}
    assert client.post("/api/courses", json=too_many_done, headers=auth).status_code == 422
    backwards = {"slots": [{"weekday": 0, "start_time": "22:00", "end_time": "20:00"}]}
    assert client.put("/api/availability", json=backwards, headers=auth).status_code == 422
    bad_time = {"slots": [{"weekday": 0, "start_time": "25:00", "end_time": "26:00"}]}
    assert client.put("/api/availability", json=bad_time, headers=auth).status_code == 422
