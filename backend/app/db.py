"""SQLite membership store. Members are created on first successful login."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    google_sub    TEXT NOT NULL UNIQUE,
    email         TEXT NOT NULL,
    name          TEXT,
    picture       TEXT,
    created_at    TEXT NOT NULL,
    last_login_at TEXT NOT NULL
);
"""


class Member(TypedDict):
    id: int
    email: str
    name: str | None
    picture: str | None
    created_at: str
    last_login_at: str


def _connect(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str) -> None:
    with closing(_connect(path)) as conn, conn:
        conn.executescript(SCHEMA)


def _row_to_member(row: sqlite3.Row) -> Member:
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
    now = datetime.now(UTC).isoformat(timespec="seconds")
    with closing(_connect(path)) as conn, conn:
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
            (google_sub, email, name, picture, now, now),
        )
        row = conn.execute(
            "SELECT * FROM users WHERE google_sub = ?", (google_sub,)
        ).fetchone()
    assert row is not None
    return _row_to_member(row)


def get_member(path: str, user_id: int) -> Member | None:
    with closing(_connect(path)) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_member(row) if row else None
