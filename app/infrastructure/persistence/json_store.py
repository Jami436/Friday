"""JSON-file adapter for the MemoryStore port (lightweight fallback)."""
import json
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


class JsonMemoryStore(MemoryStore):
    """Thread-safe JSON-file storage. Prefer SqliteMemoryStore for production use."""

    def __init__(self, path: Path, clock: Clock | None = None) -> None:
        self._path = path
        self._clock = clock or SystemClock()
        self._lock = threading.RLock()
        self._data = self._load()

    def _now_iso(self) -> str:
        return self._clock.now().isoformat(timespec="seconds")

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "tasks": [],
            "deadlines": [],
            "notes": [],
            "last_briefing_date": None,
            "last_seen_email_id": None,
        }

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def add_task(self, title: str) -> Task:
        with self._lock:
            task = Task(id=str(uuid.uuid4()), title=title, created=self._now_iso())
            self._data["tasks"].append(
                {"id": task.id, "title": task.title, "done": False, "created": task.created}
            )
            self._save()
            return task

    def pending_tasks(self) -> list[Task]:
        with self._lock:
            return [
                Task(id=t["id"], title=t["title"], done=bool(t.get("done", False)), created=t.get("created", ""))
                for t in self._data["tasks"]
                if not t.get("done")
            ]

    def complete_task(self, task_id: str) -> bool:
        with self._lock:
            for t in self._data["tasks"]:
                if t["id"] == task_id and not t.get("done"):
                    t["done"] = True
                    self._save()
                    return True
            return False

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            before = len(self._data["tasks"])
            self._data["tasks"] = [t for t in self._data["tasks"] if t["id"] != task_id]
            if len(self._data["tasks"]) == before:
                return False
            self._save()
            return True

    def complete_deadline(self, deadline_id: str) -> bool:
        with self._lock:
            for d in self._data["deadlines"]:
                if d["id"] == deadline_id and not d.get("done"):
                    d["done"] = True
                    self._save()
                    return True
            return False

    def delete_deadline(self, deadline_id: str) -> bool:
        with self._lock:
            before = len(self._data["deadlines"])
            self._data["deadlines"] = [d for d in self._data["deadlines"] if d["id"] != deadline_id]
            if len(self._data["deadlines"]) == before:
                return False
            self._save()
            return True

    def reschedule_deadline(self, deadline_id: str, due_date: str, due_time: str = "") -> bool:
        with self._lock:
            for d in self._data["deadlines"]:
                if d["id"] == deadline_id:
                    d["due"] = due_date
                    d["time"] = due_time
                    d["notified"] = False
                    self._save()
                    return True
            return False

    def add_deadline(self, title: str, due_date: str, due_time: str = "") -> Deadline:
        with self._lock:
            deadline = Deadline(id=str(uuid.uuid4()), title=title, due=due_date, time=due_time, created=self._now_iso())
            self._data["deadlines"].append(
                {
                    "id": deadline.id,
                    "title": deadline.title,
                    "due": deadline.due,
                    "time": deadline.time,
                    "done": False,
                    "source": "voice",
                    "created": deadline.created,
                }
            )
            self._save()
            return deadline

    def deadlines_due_on(self, when: date) -> list[Deadline]:
        target = when.isoformat()
        with self._lock:
            return [
                Deadline(**{k: d[k] for k in ("id", "title", "due", "time", "done", "source", "created")})
                for d in self._data["deadlines"]
                if not d.get("done") and d["due"] == target
            ]

    def upcoming_deadlines(self, limit: int = 10) -> list[Deadline]:
        today = self._clock.now().date().isoformat()
        with self._lock:
            items = [d for d in self._data["deadlines"] if not d.get("done") and d["due"] >= today]
            items.sort(key=lambda d: (d["due"], d.get("time", "")))
            return [
                Deadline(**{k: d[k] for k in ("id", "title", "due", "time", "done", "source", "created")})
                for d in items[:limit]
            ]

    def deadlines_due_within(self, minutes: int = 10) -> list[Deadline]:
        now = self._clock.now()
        due: list[Deadline] = []
        with self._lock:
            for d in self._data["deadlines"]:
                if d.get("done"):
                    continue
                try:
                    due_dt = datetime.fromisoformat(f"{d['due']}T{d.get('time') or '23:59'}")
                except ValueError:
                    continue
                delta = (due_dt - now).total_seconds()
                keys = ("id", "title", "due", "time", "done", "source", "created")
                if -90 <= delta <= minutes * 60:
                    due.append(Deadline(**{k: d[k] for k in keys}))
        return due

    def deadline_notified(self, deadline_id: str) -> bool:
        with self._lock:
            for d in self._data["deadlines"]:
                if d["id"] == deadline_id:
                    return bool(d.get("notified", False))
            return False

    def mark_deadline_notified(self, deadline_id: str) -> None:
        with self._lock:
            for d in self._data["deadlines"]:
                if d["id"] == deadline_id:
                    d["notified"] = True
                    self._save()
                    return

    def add_note(self, text: str) -> Note:
        with self._lock:
            note = Note(id=str(uuid.uuid4()), text=text, created=self._now_iso())
            self._data["notes"].append({"id": note.id, "text": note.text, "created": note.created})
            self._save()
            return note

    def notes(self, limit: int = 20) -> list[Note]:
        with self._lock:
            return [
                Note(id=n["id"], text=n["text"], created=n.get("created", ""))
                for n in reversed(self._data["notes"][-limit:])
            ]

    def briefing_done_today(self) -> bool:
        with self._lock:
            return self._data.get("last_briefing_date") == self._clock.now().date().isoformat()

    def mark_briefing_done(self) -> None:
        with self._lock:
            self._data["last_briefing_date"] = self._clock.now().date().isoformat()
            self._save()

    def get_last_seen_email_id(self) -> str | None:
        with self._lock:
            return self._data.get("last_seen_email_id")

    def set_last_seen_email_id(self, email_id: str) -> None:
        with self._lock:
            self._data["last_seen_email_id"] = email_id
            self._save()
