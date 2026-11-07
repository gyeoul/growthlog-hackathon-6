"""SQLite storage: members and their growth-log entries.

The database file is the source of truth for everything the app saves. Schema
changes go through `MIGRATIONS`, so an existing app.db is upgraded in place
instead of being recreated.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict


@dataclass(frozen=True)
class Migration:
    """One schema step. `table` lets a legacy database adopt an existing table."""

    table: str
    sql: str


# Append-only. Each entry runs exactly once per database file; never edit or
# reorder a past entry — add a new one.
MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        table="users",
        sql="""
        CREATE TABLE users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            google_sub    TEXT NOT NULL UNIQUE,
            email         TEXT NOT NULL,
            name          TEXT,
            picture       TEXT,
            created_at    TEXT NOT NULL,
            last_login_at TEXT NOT NULL
        );
        """,
    ),
    Migration(
        table="entries",
        sql="""
        CREATE TABLE entries (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title      TEXT NOT NULL,
            content    TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX idx_entries_user ON entries(user_id, updated_at DESC);
        """,
    ),
    Migration(
        table="semesters",
        sql="""
        CREATE TABLE semesters (
            user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            start_date TEXT NOT NULL,
            end_date   TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
    ),
    Migration(
        table="courses",
        sql="""
        CREATE TABLE courses (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name                TEXT NOT NULL,
            credits             INTEGER NOT NULL DEFAULT 3,
            total_lectures      INTEGER NOT NULL DEFAULT 15,
            done_lectures       INTEGER NOT NULL DEFAULT 0,
            minutes_per_lecture INTEGER NOT NULL DEFAULT 50,
            created_at          TEXT NOT NULL
        );
        CREATE INDEX idx_courses_user ON courses(user_id, id);
        """,
    ),
    Migration(
        table="deadlines",
        sql="""
        CREATE TABLE deadlines (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            course_id  INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
            kind       TEXT NOT NULL,
            title      TEXT NOT NULL,
            due_date   TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX idx_deadlines_user ON deadlines(user_id, due_date);
        """,
    ),
    Migration(
        table="availability",
        sql="""
        CREATE TABLE availability (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            weekday    INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time   TEXT NOT NULL
        );
        CREATE INDEX idx_availability_user ON availability(user_id, weekday);
        """,
    ),
    Migration(
        table="plan_blocks",
        sql="""
        CREATE TABLE plan_blocks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            course_id   INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
            deadline_id INTEGER REFERENCES deadlines(id) ON DELETE CASCADE,
            kind        TEXT NOT NULL,
            title       TEXT NOT NULL,
            date        TEXT NOT NULL,
            start_time  TEXT NOT NULL,
            end_time    TEXT NOT NULL,
            done        INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL
        );
        CREATE INDEX idx_plan_blocks_user ON plan_blocks(user_id, date, start_time);
        """,
    ),
)


class Member(TypedDict):
    id: int
    email: str
    name: str | None
    picture: str | None
    created_at: str
    last_login_at: str


class Entry(TypedDict):
    id: int
    title: str
    content: str
    created_at: str
    updated_at: str


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    # WAL survives crashes better and lets reads proceed during a write.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def session(path: str) -> Iterator[sqlite3.Connection]:
    """Connection that commits on success and rolls back on error."""
    conn = connect(path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return row is not None


def init_db(path: str) -> None:
    """Create the file and apply every migration it has not seen yet.

    A database written by an older build (tables present, no schema_version) is
    adopted rather than rejected: an existing table counts as that migration
    having been applied, so no data is ever dropped.
    """
    with session(path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version ("
            " version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
        current = int(row[0])
        for version, migration in enumerate(MIGRATIONS, start=1):
            if version <= current:
                continue
            if not _table_exists(conn, migration.table):
                conn.executescript(migration.sql)
            conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (version, now()),
            )


# --- members -------------------------------------------------------------


def _member(row: sqlite3.Row) -> Member:
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "picture": row["picture"],
        "created_at": row["created_at"],
        "last_login_at": row["last_login_at"],
    }


def upsert_member(
    path: str, *, google_sub: str, email: str, name: str | None, picture: str | None
) -> Member:
    """Create the member on first login, refresh their profile afterwards."""
    stamp = now()
    with session(path) as conn:
        conn.execute(
            """
            INSERT INTO users (google_sub, email, name, picture, created_at, last_login_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(google_sub) DO UPDATE SET
                email = excluded.email,
                name = excluded.name,
                picture = excluded.picture,
                last_login_at = excluded.last_login_at
            """,
            (google_sub, email, name, picture, stamp, stamp),
        )
        row = conn.execute(
            "SELECT * FROM users WHERE google_sub = ?", (google_sub,)
        ).fetchone()
    return _member(row)


def get_member(path: str, user_id: int) -> Member | None:
    with session(path) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _member(row) if row else None


# --- entries -------------------------------------------------------------


def create_entry(path: str, user_id: int, title: str, content: str) -> Entry:
    stamp = now()
    with session(path) as conn:
        cur = conn.execute(
            "INSERT INTO entries (user_id, title, content, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, title, content, stamp, stamp),
        )
        row = conn.execute(
            "SELECT id, title, content, created_at, updated_at FROM entries WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    return dict(row)  # type: ignore[return-value]


def list_entries(path: str, user_id: int, limit: int = 100) -> list[Entry]:
    with session(path) as conn:
        rows = conn.execute(
            "SELECT id, title, content, created_at, updated_at FROM entries"
            " WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]  # type: ignore[misc]


def get_entry(path: str, user_id: int, entry_id: int) -> Entry | None:
    with session(path) as conn:
        row = conn.execute(
            "SELECT id, title, content, created_at, updated_at FROM entries"
            " WHERE id = ? AND user_id = ?",
            (entry_id, user_id),
        ).fetchone()
    return dict(row) if row else None  # type: ignore[return-value]


def update_entry(
    path: str, user_id: int, entry_id: int, title: str, content: str
) -> Entry | None:
    with session(path) as conn:
        cur = conn.execute(
            "UPDATE entries SET title = ?, content = ?, updated_at = ?"
            " WHERE id = ? AND user_id = ?",
            (title, content, now(), entry_id, user_id),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute(
            "SELECT id, title, content, created_at, updated_at FROM entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
    return dict(row)  # type: ignore[return-value]


def delete_entry(path: str, user_id: int, entry_id: int) -> bool:
    with session(path) as conn:
        cur = conn.execute(
            "DELETE FROM entries WHERE id = ? AND user_id = ?", (entry_id, user_id)
        )
        return cur.rowcount > 0


def stats(path: str) -> dict[str, int]:
    with closing(connect(path)) as conn:
        return {
            "members": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "entries": conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0],
        }


# --- semester planner ----------------------------------------------------
# Dates are ISO `YYYY-MM-DD`, times `HH:MM`; both sort correctly as text.


class Semester(TypedDict):
    start_date: str
    end_date: str


class Course(TypedDict):
    id: int
    name: str
    credits: int
    total_lectures: int
    done_lectures: int
    minutes_per_lecture: int


class Deadline(TypedDict):
    id: int
    course_id: int
    kind: str
    title: str
    due_date: str


class Slot(TypedDict):
    weekday: int
    start_time: str
    end_time: str


class PlanBlock(TypedDict):
    id: int
    course_id: int
    deadline_id: int | None
    kind: str
    title: str
    date: str
    start_time: str
    end_time: str
    done: bool


_COURSE_COLS = "id, name, credits, total_lectures, done_lectures, minutes_per_lecture"
_DEADLINE_COLS = "id, course_id, kind, title, due_date"
_BLOCK_COLS = "id, course_id, deadline_id, kind, title, date, start_time, end_time, done"


def _block(row: sqlite3.Row) -> PlanBlock:
    block = dict(row)
    block["done"] = bool(block["done"])
    return block  # type: ignore[return-value]


def get_semester(path: str, user_id: int) -> Semester | None:
    with session(path) as conn:
        row = conn.execute(
            "SELECT start_date, end_date FROM semesters WHERE user_id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None  # type: ignore[return-value]


def set_semester(path: str, user_id: int, start_date: str, end_date: str) -> Semester:
    with session(path) as conn:
        conn.execute(
            """
            INSERT INTO semesters (user_id, start_date, end_date, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                updated_at = excluded.updated_at
            """,
            (user_id, start_date, end_date, now()),
        )
    return {"start_date": start_date, "end_date": end_date}


def list_courses(path: str, user_id: int) -> list[Course]:
    with session(path) as conn:
        rows = conn.execute(
            f"SELECT {_COURSE_COLS} FROM courses WHERE user_id = ? ORDER BY id", (user_id,)
        ).fetchall()
    return [dict(row) for row in rows]  # type: ignore[misc]


def get_course(path: str, user_id: int, course_id: int) -> Course | None:
    with session(path) as conn:
        row = conn.execute(
            f"SELECT {_COURSE_COLS} FROM courses WHERE id = ? AND user_id = ?",
            (course_id, user_id),
        ).fetchone()
    return dict(row) if row else None  # type: ignore[return-value]


def create_course(
    path: str,
    user_id: int,
    *,
    name: str,
    credits: int,
    total_lectures: int,
    done_lectures: int,
    minutes_per_lecture: int,
) -> Course:
    with session(path) as conn:
        cur = conn.execute(
            "INSERT INTO courses (user_id, name, credits, total_lectures, done_lectures,"
            " minutes_per_lecture, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, name, credits, total_lectures, done_lectures, minutes_per_lecture, now()),
        )
        row = conn.execute(
            f"SELECT {_COURSE_COLS} FROM courses WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)  # type: ignore[return-value]


def update_course(
    path: str,
    user_id: int,
    course_id: int,
    *,
    name: str,
    credits: int,
    total_lectures: int,
    done_lectures: int,
    minutes_per_lecture: int,
) -> Course | None:
    with session(path) as conn:
        cur = conn.execute(
            "UPDATE courses SET name = ?, credits = ?, total_lectures = ?, done_lectures = ?,"
            " minutes_per_lecture = ? WHERE id = ? AND user_id = ?",
            (name, credits, total_lectures, done_lectures, minutes_per_lecture, course_id, user_id),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute(
            f"SELECT {_COURSE_COLS} FROM courses WHERE id = ?", (course_id,)
        ).fetchone()
    return dict(row)  # type: ignore[return-value]


def delete_course(path: str, user_id: int, course_id: int) -> bool:
    with session(path) as conn:
        cur = conn.execute(
            "DELETE FROM courses WHERE id = ? AND user_id = ?", (course_id, user_id)
        )
        return cur.rowcount > 0


def list_deadlines(path: str, user_id: int) -> list[Deadline]:
    with session(path) as conn:
        rows = conn.execute(
            f"SELECT {_DEADLINE_COLS} FROM deadlines WHERE user_id = ?"
            " ORDER BY due_date, id",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]  # type: ignore[misc]


def create_deadline(
    path: str, user_id: int, *, course_id: int, kind: str, title: str, due_date: str
) -> Deadline:
    with session(path) as conn:
        cur = conn.execute(
            "INSERT INTO deadlines (user_id, course_id, kind, title, due_date, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, course_id, kind, title, due_date, now()),
        )
        row = conn.execute(
            f"SELECT {_DEADLINE_COLS} FROM deadlines WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)  # type: ignore[return-value]


def delete_deadline(path: str, user_id: int, deadline_id: int) -> bool:
    with session(path) as conn:
        cur = conn.execute(
            "DELETE FROM deadlines WHERE id = ? AND user_id = ?", (deadline_id, user_id)
        )
        return cur.rowcount > 0


def list_availability(path: str, user_id: int) -> list[Slot]:
    with session(path) as conn:
        rows = conn.execute(
            "SELECT weekday, start_time, end_time FROM availability WHERE user_id = ?"
            " ORDER BY weekday, start_time",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]  # type: ignore[misc]


def replace_availability(path: str, user_id: int, slots: list[Slot]) -> list[Slot]:
    """The weekly pattern is edited as a whole, so it is saved as a whole."""
    with session(path) as conn:
        conn.execute("DELETE FROM availability WHERE user_id = ?", (user_id,))
        conn.executemany(
            "INSERT INTO availability (user_id, weekday, start_time, end_time)"
            " VALUES (?, ?, ?, ?)",
            [(user_id, s["weekday"], s["start_time"], s["end_time"]) for s in slots],
        )
    return list_availability(path, user_id)


def list_blocks(
    path: str, user_id: int, start: str | None = None, end: str | None = None
) -> list[PlanBlock]:
    """Blocks with `start <= date <= end`; either bound may be omitted."""
    with session(path) as conn:
        rows = conn.execute(
            f"SELECT {_BLOCK_COLS} FROM plan_blocks WHERE user_id = ?"
            " AND date >= COALESCE(?, date) AND date <= COALESCE(?, date)"
            " ORDER BY date, start_time, id",
            (user_id, start, end),
        ).fetchall()
    return [_block(row) for row in rows]


def replace_open_blocks(path: str, user_id: int, today: str, blocks: list[dict]) -> None:
    """Drop unfinished blocks from today on and store a fresh plan in their place.

    Past blocks and finished blocks are history and are never touched.
    """
    stamp = now()
    with session(path) as conn:
        conn.execute(
            "DELETE FROM plan_blocks WHERE user_id = ? AND done = 0 AND date >= ?",
            (user_id, today),
        )
        conn.executemany(
            "INSERT INTO plan_blocks (user_id, course_id, deadline_id, kind, title, date,"
            " start_time, end_time, done, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
            [
                (
                    user_id,
                    b["course_id"],
                    b["deadline_id"],
                    b["kind"],
                    b["title"],
                    b["date"],
                    b["start_time"],
                    b["end_time"],
                    stamp,
                )
                for b in blocks
            ],
        )


def set_block_done(path: str, user_id: int, block_id: int, done: bool) -> PlanBlock | None:
    with session(path) as conn:
        cur = conn.execute(
            "UPDATE plan_blocks SET done = ? WHERE id = ? AND user_id = ?",
            (int(done), block_id, user_id),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute(
            f"SELECT {_BLOCK_COLS} FROM plan_blocks WHERE id = ?", (block_id,)
        ).fetchone()
    return _block(row)
