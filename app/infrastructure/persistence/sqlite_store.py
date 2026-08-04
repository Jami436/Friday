"""SQLite adapter for the MemoryStore port."""
import sqlite3
import threading
import uuid
from datetime import date, datetime
from pathlib import Path

from app.domain.entities.deadline import Deadline
from app.domain.entities.note import Note
from app.domain.entities.task import Task
from app.domain.ports.clock import Clock
from app.domain.ports.memory import MemoryStore
from app.domain.services.clock import SystemClock

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS deadlines (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    due TEXT NOT NULL,
    time TEXT NOT NULL DEFAULT '',
    done INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'voice',
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class SqliteMemoryStore(MemoryStore):
    """Thread-safe SQLite-backed storage of the user's personal matters."""

    def __init__(self, path: Path, clock: Clock | None = None) -> None:
        self._path = path
        self._clock = clock or SystemClock()
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def _now_iso(self) -> str:
        return self._clock.now().isoformat(timespec="seconds")

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---- tasks ----

    def add_task(self, title: str) -> Task:
        with self._lock:
            task_id = str(uuid.uuid4())
            created = self._now_iso()
            self._conn.execute(
                "INSERT INTO tasks (id, title, done, created) VALUES (?, ?, 0, ?)",
                (task_id, title, created),
            )
            self._conn.commit()
            return Task(id=task_id, title=title, created=created)

    def pending_tasks(self) -> list[Task]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM tasks WHERE done = 0 ORDER BY created"
            ).fetchall()
            return [Task(id=r["id"], title=r["title"], done=bool(r["done"]), created=r["created"]) for r in rows]

    # ---- deadlines ----

    def add_deadline(self, title: str, due_date: str, due_time: str = "") -> Deadline:
        with self._lock:
            deadline_id = str(uuid.uuid4())
            created = self._now_iso()
            self._conn.execute(
                "INSERT INTO deadlines (id, title, due, time, done, source, created) "
                "VALUES (?, ?, ?, ?, 0, 'voice', ?)",
                (deadline_id, title, due_date, due_time, created),
            )
            self._conn.commit()
            return Deadline(id=deadline_id, title=title, due=due_date, time=due_time, created=created)

    @staticmethod
    def _row_to_deadline(row: sqlite3.Row) -> Deadline:
        return Deadline(
            id=row["id"],
            title=row["title"],
            due=row["due"],
            time=row["time"],
            done=bool(row["done"]),
            source=row["source"],
            created=row["created"],
        )

    def deadlines_due_on(self, when: date) -> list[Deadline]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM deadlines WHERE done = 0 AND due = ?", (when.isoformat(),)
            ).fetchall()
            return [self._row_to_deadline(r) for r in rows]

    def upcoming_deadlines(self, limit: int = 10) -> list[Deadline]:
        today = self._clock.now().date().isoformat()
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM deadlines WHERE done = 0 AND due >= ? "
                "ORDER BY due, time LIMIT ?",
                (today, limit),
            ).fetchall()
            return [self._row_to_deadline(r) for r in rows]

    def deadlines_due_within(self, minutes: int = 10) -> list[Deadline]:
        now = self._clock.now()
        due: list[Deadline] = []
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM deadlines WHERE done = 0"
            ).fetchall()
            for row in rows:
                deadline = self._row_to_deadline(row)
                try:
                    due_dt = datetime.fromisoformat(f"{deadline.due}T{deadline.time or '23:59'}")
                except ValueError:
                    continue
                delta = (due_dt - now).total_seconds()
                if -90 <= delta <= minutes * 60:
                    due.append(deadline)
        return due

    # ---- notes ----

    def add_note(self, text: str) -> Note:
        with self._lock:
            note_id = str(uuid.uuid4())
            created = self._now_iso()
            self._conn.execute(
                "INSERT INTO notes (id, text, created) VALUES (?, ?, ?)",
                (note_id, text, created),
            )
            self._conn.commit()
            return Note(id=note_id, text=text, created=created)

    def notes(self, limit: int = 20) -> list[Note]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM notes ORDER BY created DESC LIMIT ?", (limit,)
            ).fetchall()
            return [Note(id=r["id"], text=r["text"], created=r["created"]) for r in rows]

    # ---- state ----

    def _meta_get(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def _meta_set(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self._conn.commit()

    def briefing_done_today(self) -> bool:
        with self._lock:
            return self._meta_get("last_briefing_date") == self._clock.now().date().isoformat()

    def mark_briefing_done(self) -> None:
        with self._lock:
            self._meta_set("last_briefing_date", self._clock.now().date().isoformat())

    def get_last_seen_email_id(self) -> str | None:
        with self._lock:
            return self._meta_get("last_seen_email_id")

    def set_last_seen_email_id(self, email_id: str) -> None:
        with self._lock:
            self._meta_set("last_seen_email_id", email_id)
