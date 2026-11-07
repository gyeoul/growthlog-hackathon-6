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
