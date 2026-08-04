from datetime import date

import numpy as np
import pytest

from app.application.assistant_service import AssistantService
from app.application.briefing_service import BriefingService
from app.application.conversation_service import ConversationService
from app.application.memory_extractor import MemoryExtractor
from app.infrastructure.persistence.sqlite_store import SqliteMemoryStore
from tests.fakes import FakeAIProvider, FakeClock, FakeEmailProvider, FakeSTT, FakeTTS, FakeVAD, FakeWakeEngine


@pytest.fixture
def components(tmp_path):
    clock = FakeClock()
    store = SqliteMemoryStore(tmp_path / "test.db", clock=clock)
    email = FakeEmailProvider()
    tts = FakeTTS()
    ai = FakeAIProvider()
    return {
        "store": store,
        "clock": clock,
        "email": email,
        "tts": tts,
        "ai": ai,
    }


def test_memory_extractor_parses_json(components):
    ai = FakeAIProvider(queue=['[{"type": "deadline", "title": "Pay rent", "due": "2026-08-05"}]'])
    extractor = MemoryExtractor(ai)
    actions = extractor.extract("Remind me to pay rent on the 5th")
    assert actions == [{"type": "deadline", "title": "Pay rent", "due": "2026-08-05"}]


def test_memory_extractor_tolerates_non_json(components):
    ai = FakeAIProvider(queue=["sure thing"])
    extractor = MemoryExtractor(ai)
    assert extractor.extract("What time is it?") == []


def test_memory_extractor_skips_llm_for_non_action_requests(components):
    ai = FakeAIProvider(queue=['[{"type": "deadline", "title": "Pay rent", "due": "2026-08-05"}]'])
    extractor = MemoryExtractor(ai)
    assert extractor.extract("Tell me a joke") == []
    assert extractor.extract("How are you doing?") == []
    assert ai.requests == []  # LLM never called


def test_memory_extractor_uses_injected_clock_for_relative_dates(components):
    clock = components["clock"]
    ai = FakeAIProvider(queue=['[{"type": "deadline", "title": "Pay rent", "due": "2026-08-04"}]'])
    extractor = MemoryExtractor(ai, clock=clock)
    actions = extractor.extract("Remind me to pay rent tomorrow")
    assert actions == [{"type": "deadline", "title": "Pay rent", "due": "2026-08-04"}]
    assert "2026-08-03" in ai.requests[0]  # today from clock, not date.today()


def test_assistant_persists_deadline(components):
    store, clock, email = components["store"], components["clock"], components["email"]
    ai = FakeAIProvider(
        queue=['[{"type": "deadline", "title": "Submit report", "due": "2026-08-10"}]'],
        default="Done, Boss.",
    )
    briefing = BriefingService(store=store, email=email, clock=clock)
    assistant = AssistantService(ai=ai, store=store, briefing=briefing, clock=clock)
    reply = assistant.respond("Set a deadline for the report on August 10th")
    assert "Boss" in reply.text
    assert "Submit report" in reply.confirmations[0]
    assert store.deadlines_due_on(date(2026, 8, 10))[0].title == "Submit report"


def test_conversation_goodbye_returns(components):
    store, clock, email, tts = (
        components["store"], components["clock"], components["email"], components["tts"],
    )
    ai = FakeAIProvider()
    briefing = BriefingService(store=store, email=email, clock=clock)
    assistant = AssistantService(ai=ai, store=store, briefing=briefing, clock=clock)
    conversation = ConversationService(
        assistant=assistant, tts=tts, stt=FakeSTT(["goodbye"]), vad=FakeVAD(), clock=clock
    )
    conversation.run()
    assert tts.spoken[0] == "Yes, Boss?"
    assert "Right away" in tts.spoken[-1]


def test_conversation_speaks_confirmation_after_reply(components):
    store, clock, email, tts = (
        components["store"], components["clock"], components["email"], components["tts"],
    )
    ai = FakeAIProvider(
        queue=['[{"type": "deadline", "title": "Submit report", "due": "2026-08-10"}]'],
        default="Done, Boss.",
    )
    briefing = BriefingService(store=store, email=email, clock=clock)
    assistant = AssistantService(ai=ai, store=store, briefing=briefing, clock=clock)
    conversation = ConversationService(
        assistant=assistant,
        tts=tts,
        stt=FakeSTT(["Set a deadline for the report on August 10th", "goodbye"]),
        vad=FakeVAD(),
        clock=clock,
    )
    conversation.run()
    assert tts.spoken[1] == "Done, Boss."
    assert "Submit report" in tts.spoken[2]


def test_reminder_speaks_each_deadline_once(components, tmp_path):
    store, clock, email, tts = (
        components["store"], components["clock"], components["email"], components["tts"],
    )
    from app.application.reminder_service import ReminderService
    store.add_deadline("Standup", clock.now().strftime("%Y-%m-%d"), clock.now().strftime("%H:%M"))
    reminders = ReminderService(store=store, tts=tts, clock=clock)
    assert reminders.check_and_notify(minutes=10) == 1
    assert reminders.check_and_notify(minutes=10) == 0  # not repeated
    assert len(tts.spoken) == 1


def test_reminder_notification_persists_across_restarts(components, tmp_path):
    from pathlib import Path

    from app.application.reminder_service import ReminderService
    path = tmp_path / "restart.db"
    clock = FakeClock()
    tts = FakeTTS()

    first_store = SqliteMemoryStore(path, clock=clock)
    deadline = first_store.add_deadline("Standup", clock.now().strftime("%Y-%m-%d"), clock.now().strftime("%H:%M"))
    first_store.close()

    second_store = SqliteMemoryStore(path, clock=clock)
    second_tts = FakeTTS()
    reminders = ReminderService(store=second_store, tts=second_tts, clock=clock)
    assert reminders.check_and_notify(minutes=10) == 1
    assert len(second_tts.spoken) == 1

    third_tts = FakeTTS()
    reminders_again = ReminderService(store=second_store, tts=third_tts, clock=clock)
    assert reminders_again.check_and_notify(minutes=10) == 0  # persisted, not re-spoken
    assert len(third_tts.spoken) == 0
    second_store.close()
