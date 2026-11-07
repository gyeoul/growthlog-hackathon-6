"""Semester planner: turns what is left to study into dated timetable blocks.

Pure functions with no I/O, so the scheduling rules are tested directly. The
rules, in order of importance:

1. Work is split into tasks: one per remaining lecture, a few prep sessions per
   assignment / attendance class, and review sessions before each exam.
2. Tasks fill the member's weekly free time earliest-deadline-first.
3. Back-to-back blocks of the same course are avoided when another course's
   task is nearly as urgent, so a long evening is not one subject.
4. A task that cannot fit before its deadline is reported, never silently
   dropped or placed late.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from app.db import Course, Deadline, PlanBlock, Slot

LECTURE_BUFFER_DAYS = 7  # finish lectures a week before the course's exam
REVIEW_WINDOW_DAYS = 14  # exam review starts at most two weeks out
SESSION_MINUTES = 60
ASSIGNMENT_SESSIONS = 3
ATTENDANCE_SESSIONS = 1
REVIEW_SESSIONS_PER_CREDIT = 2
INTERLEAVE_SLACK_DAYS = 7

DEADLINE_KINDS = ("assignment", "attendance", "exam")


@dataclass(frozen=True)
class Task:
    course_id: int
    deadline_id: int | None
    kind: str  # lecture | assignment | attendance | review
    title: str
    minutes: int
    first_day: date
    last_day: date
    order: int  # keeps lecture 3 ahead of lecture 4 when deadlines tie


def to_minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def _hhmm(total: int) -> str:
    return f"{total // 60:02d}:{total % 60:02d}"


def build_tasks(
    today: date,
    semester_end: date,
    courses: list[Course],
    deadlines: list[Deadline],
    done_blocks: list[PlanBlock],
) -> list[Task]:
    """Everything still to do, each with the window it has to happen in."""
    tasks: list[Task] = []
    order = 0

    def add(**kwargs) -> None:
        nonlocal order
        tasks.append(Task(order=order, **kwargs))
        order += 1

    done_lectures: dict[int, int] = {}
    done_sessions: dict[int, int] = {}
    for block in done_blocks:
        if block["kind"] == "lecture":
            done_lectures[block["course_id"]] = done_lectures.get(block["course_id"], 0) + 1
        elif block["deadline_id"] is not None:
            done_sessions[block["deadline_id"]] = done_sessions.get(block["deadline_id"], 0) + 1

    upcoming = [d for d in deadlines if date.fromisoformat(d["due_date"]) > today]

    for course in courses:
        exams = sorted(
            date.fromisoformat(d["due_date"])
            for d in upcoming
            if d["course_id"] == course["id"] and d["kind"] == "exam"
        )
        if exams:
            buffered = exams[0] - timedelta(days=LECTURE_BUFFER_DAYS)
            lecture_last = buffered if buffered >= today else exams[0] - timedelta(days=1)
        else:
            lecture_last = semester_end
        lecture_last = max(today, lecture_last)

        finished = course["done_lectures"] + done_lectures.get(course["id"], 0)
        for number in range(finished + 1, course["total_lectures"] + 1):
            add(
                course_id=course["id"],
                deadline_id=None,
                kind="lecture",
                title=f"{course['name']} {number}강",
                minutes=course["minutes_per_lecture"],
                first_day=today,
                last_day=lecture_last,
            )

    credits = {c["id"]: c["credits"] for c in courses}
    names = {c["id"]: c["name"] for c in courses}
    for deadline in upcoming:
        course_id = deadline["course_id"]
        if course_id not in names:
            continue
        due = date.fromisoformat(deadline["due_date"])
        kind = deadline["kind"]
        if kind == "exam":
            needed = max(1, credits[course_id] * REVIEW_SESSIONS_PER_CREDIT)
            first_day = max(today, due - timedelta(days=REVIEW_WINDOW_DAYS))
            label, block_kind = "시험 복습", "review"
        elif kind == "attendance":
            needed, first_day = ATTENDANCE_SESSIONS, today
            label, block_kind = "출석수업 준비", "attendance"
        else:
            needed, first_day = ASSIGNMENT_SESSIONS, today
            label, block_kind = "과제 준비", "assignment"

        done = done_sessions.get(deadline["id"], 0)
        for session in range(done + 1, needed + 1):
            suffix = f" ({session}/{needed})" if needed > 1 else ""
            add(
                course_id=course_id,
                deadline_id=deadline["id"],
                kind=block_kind,
                title=f"{names[course_id]} {label}{suffix}",
                minutes=SESSION_MINUTES,
                first_day=first_day,
                last_day=due - timedelta(days=1),
            )

    return tasks


def _free_intervals(
    day: date,
    availability: list[Slot],
    occupied: list[PlanBlock],
    not_before: int,
) -> list[tuple[int, int]]:
    """The day's free minutes as [start, end) pairs, minus blocks already kept."""
    iso = day.isoformat()
    taken = sorted(
        (to_minutes(b["start_time"]), to_minutes(b["end_time"]))
        for b in occupied
        if b["date"] == iso
    )
    free: list[tuple[int, int]] = []
    for slot in sorted(availability, key=lambda s: s["start_time"]):
        if slot["weekday"] != day.weekday():
            continue
        cursor = max(to_minutes(slot["start_time"]), not_before)
        end = to_minutes(slot["end_time"])
        for busy_start, busy_end in taken:
            if busy_end <= cursor or busy_start >= end:
                continue
            if busy_start > cursor:
                free.append((cursor, busy_start))
            cursor = max(cursor, busy_end)
        if cursor < end:
            free.append((cursor, end))
    return free


def _pick(pending: list[Task], day: date, room: int, last_course: int | None) -> Task | None:
    eligible = [t for t in pending if t.first_day <= day and t.minutes <= room]
    if not eligible:
        return None
    first = eligible[0]
    if first.course_id != last_course:
        return first
    slack = first.last_day + timedelta(days=INTERLEAVE_SLACK_DAYS)
    other = next(
        (t for t in eligible if t.course_id != last_course and t.last_day <= slack), None
    )
    return other or first


def schedule(
    today: date,
    semester_end: date,
    tasks: list[Task],
    availability: list[Slot],
    occupied: list[PlanBlock],
    now_minutes: int = 0,
) -> tuple[list[dict], list[Task]]:
    """Place tasks into free time. Returns (new blocks, tasks that did not fit)."""
    pending = sorted(tasks, key=lambda t: (t.last_day, t.order))
    placed: list[dict] = []
    unplaced: list[Task] = []

    day = today
    while day <= semester_end and pending:
        last_course: int | None = None
        not_before = now_minutes if day == today else 0
        for start, end in _free_intervals(day, availability, occupied, not_before):
            cursor = start
            while True:
                task = _pick(pending, day, end - cursor, last_course)
                if task is None:
                    break
                pending.remove(task)
                placed.append(
                    {
                        "course_id": task.course_id,
                        "deadline_id": task.deadline_id,
                        "kind": task.kind,
                        "title": task.title,
                        "date": day.isoformat(),
                        "start_time": _hhmm(cursor),
                        "end_time": _hhmm(cursor + task.minutes),
                    }
                )
                cursor += task.minutes
                last_course = task.course_id

        unplaced.extend(t for t in pending if t.last_day <= day)
        pending = [t for t in pending if t.last_day > day]
        day += timedelta(days=1)

    unplaced.extend(pending)
    return placed, unplaced
