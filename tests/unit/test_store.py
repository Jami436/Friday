from datetime import date, datetime

import pytest

from app.infrastructure.persistence.json_store import JsonMemoryStore
from app.infrastructure.persistence.sqlite_store import SqliteMemoryStore

PARAMS = [
    pytest.param(SqliteMemoryStore, id="sqlite"),
    pytest.param(JsonMemoryStore, id="json"),
]


@pytest.fixture(params=PARAMS)
def store(tmp_path, request):
    store_cls = request.param
    path = tmp_path / ("store.db" if store_cls is SqliteMemoryStore else "store.json")
    instance = store_cls(path)
    yield instance
    close = getattr(instance, "close", None)
    if close:
        close()


def test_add_and_list_deadlines(store):
    store.add_deadline("Submit report", "2026-08-10", "14:00")
    due = store.deadlines_due_on(date(2026, 8, 10))
    assert len(due) == 1
    assert due[0].title == "Submit report"
    assert store.upcoming_deadlines()[0].title == "Submit report"


def test_deadlines_due_within_window(store):
    soon = datetime.now().strftime("%Y-%m-%d")
    store.add_deadline("Call boss", soon, datetime.now().strftime("%H:%M"))
    store.add_deadline("Far future", "2099-01-01")
    due = store.deadlines_due_within(minutes=10)
    assert [d.title for d in due] == ["Call boss"]


def test_briefing_done_tracking(store):
    assert store.briefing_done_today() is False
    store.mark_briefing_done()
    assert store.briefing_done_today() is True


def test_add_task_and_note(store):
    task = store.add_task("Buy coffee")
    assert store.pending_tasks()[0].id == task.id
    store.add_note("Remember the umbrella")
    assert store.notes(1)[0].text == "Remember the umbrella"


def test_email_state_roundtrip(store):
    assert store.get_last_seen_email_id() is None
    store.set_last_seen_email_id("12345")
    assert store.get_last_seen_email_id() == "12345"


def test_deadline_notification_state(store):
    deadline = store.add_deadline("Standup", "2026-08-05", "09:30")
    assert store.deadline_notified(deadline.id) is False
    store.mark_deadline_notified(deadline.id)
    assert store.deadline_notified(deadline.id) is True
    assert store.deadline_notified("missing-id") is False
