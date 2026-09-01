"""Tests for the new action types and interruptible conversation."""
from datetime import date

import pytest

from app.application.assistant_service import AssistantService
from app.application.briefing_service import BriefingService
from app.application.conversation_service import ConversationService
from app.infrastructure.persistence.sqlite_store import SqliteMemoryStore
from tests.fakes import (
    FakeAIProvider,
    FakeClock,
    FakeEmailProvider,
    FakeSTT,
    FakeTTS,
    FakeVAD,
    FakeWakeEngine,
)


@pytest.fixture
def env(tmp_path):
    clock = FakeClock()
    store = SqliteMemoryStore(tmp_path / "test.db", clock=clock)
    email = FakeEmailProvider()
    tts = FakeTTS()
    ai = FakeAIProvider()
    briefing = BriefingService(store=store, email=email, clock=clock)
    yield {
        "store": store,
        "clock": clock,
        "email": email,
        "tts": tts,
        "ai": ai,
        "briefing": briefing,
    }
    store.close()


def _assistant(env, queue=None, default="Done, Boss."):
    ai = FakeAIProvider(queue=queue, default=default)
    return AssistantService(ai=ai, store=env["store"], briefing=env["briefing"], clock=env["clock"])


def test_assistant_marks_task_complete(env):
    env["store"].add_task("Buy groceries")
    assistant = _assistant(env, queue=['[{"type": "complete", "target": "task", "title": "Buy groceries"}]'])
    reply = assistant.respond("Mark buy groceries as done")
    assert any("Buy groceries" in c and "complete" in c for c in reply.confirmations)
    assert env["store"].pending_tasks() == []


def test_assistant_marks_deadline_complete(env):
    env["store"].add_deadline("Pay rent", "2026-08-10")
    assistant = _assistant(env, queue=['[{"type": "complete", "target": "deadline", "title": "Pay rent"}]'])
    reply = assistant.respond("Mark the pay rent deadline as done")
    assert any("Pay rent" in c and "complete" in c for c in reply.confirmations)
    assert env["store"].deadlines_due_on(date(2026, 8, 10)) == []


def test_assistant_deletes_task(env):
    env["store"].add_task("Old task")
    assistant = _assistant(env, queue=['[{"type": "delete", "target": "task", "title": "Old task"}]'])
    reply = assistant.respond("Delete the old task")
    assert any("Old task" in c and "Deleted" in c for c in reply.confirmations)
    assert env["store"].pending_tasks() == []


def test_assistant_deletes_deadline(env):
    env["store"].add_deadline("Cancel meeting", "2026-08-12")
    assistant = _assistant(env, queue=['[{"type": "delete", "target": "deadline", "title": "Cancel meeting"}]'])
    reply = assistant.respond("Cancel the meeting deadline")
    assert any("Cancel meeting" in c and "Deleted" in c for c in reply.confirmations)
    assert env["store"].upcoming_deadlines() == []


def test_assistant_reschedules_deadline(env):
    env["store"].add_deadline("Publish", "2026-08-15")
    assistant = _assistant(
        env,
        queue=['[{"type": "reschedule", "title": "Publish", "due": "2026-08-20", "time": "16:00"}]'],
    )
    reply = assistant.respond("Move the publish deadline to the 20th at 4pm")
    assert any("Rescheduled" in c and "Publish" in c for c in reply.confirmations)
    updated = env["store"].upcoming_deadlines()[0]
    assert updated.due == "2026-08-20"
    assert updated.time == "16:00"


def test_assistant_lists_tasks(env):
    env["store"].add_task("Buy groceries")
    env["store"].add_task("Pay bills")
    assistant = _assistant(
        env,
        queue=['[{"type": "list", "target": "task"}]'],
        default="Here you go, Boss.",
    )
    reply = assistant.respond("List my tasks")
    assert any("Buy groceries" in c and "Pay bills" in c for c in reply.confirmations)


def test_assistant_lists_deadlines(env):
    env["store"].add_deadline("Pay rent", "2026-08-10")
    assistant = _assistant(
        env,
        queue=['[{"type": "list", "target": "deadline"}]'],
        default="Here you go, Boss.",
    )
    reply = assistant.respond("What's on my schedule?")
    assert any("Pay rent" in c and "upcoming deadline" in c for c in reply.confirmations)


def test_missing_match_reports_could_not_find(env):
    assistant = _assistant(env, queue=['[{"type": "complete", "target": "task", "title": "Nope"}]'])
    reply = assistant.respond("Finish the nope task")
    assert any("couldn't find" in c for c in reply.confirmations)


def test_conversation_interrupt_skips_confirmation_speech(env):
    store, clock, email, tts = (
        env["store"], env["clock"], env["email"], env["tts"],
    )
    ai = FakeAIProvider(
        queue=['[{"type": "task", "title": "Submit report"}]'],
        default="Done, Boss.",
    )
    briefing = BriefingService(store=store, email=email, clock=clock)
    assistant = AssistantService(ai=ai, store=store, briefing=briefing, clock=clock)

    wake = FakeWakeEngine(reasons=["clap", "clap"])  # wakes during first speak -> interrupts
    conversation = ConversationService(
        assistant=assistant,
        tts=tts,
        stt=FakeSTT(["Add a task: submit report", "goodbye"]),
        vad=FakeVAD(),
        clock=clock,
        wake_engine=wake,
    )
    conversation.run()
    # First speak ('Yes, Boss?') is interrupted by the wake engine returning 'clap'.
    # That cancels and returns to the caller without speaking the confirmation.
    assert tts.spoken and tts.spoken[0] == "Yes, Boss?"
    assert not any("Submit report" in s for s in tts.spoken)
