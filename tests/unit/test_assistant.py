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


def test_assistant_persists_deadline(components):
    store, clock, email = components["store"], components["clock"], components["email"]
    ai = FakeAIProvider(
        queue=['[{"type": "deadline", "title": "Submit report", "due": "2026-08-10"}]'],
        default="Done, Boss.",
    )
    briefing = BriefingService(store=store, email=email, clock=clock)
    assistant = AssistantService(ai=ai, store=store, briefing=briefing, clock=clock)
    reply = assistant.respond("Set a deadline for the report on August 10th")
    assert "Boss" in reply
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


def test_reminder_speaks_each_deadline_once(components):
    store, clock, email, tts = (
        components["store"], components["clock"], components["email"], components["tts"],
    )
    from app.application.reminder_service import ReminderService
    store.add_deadline("Standup", clock.now().strftime("%Y-%m-%d"), clock.now().strftime("%H:%M"))
    reminders = ReminderService(store=store, tts=tts, clock=clock)
    assert reminders.check_and_notify(minutes=10) == 1
    assert reminders.check_and_notify(minutes=10) == 0  # not repeated
    assert len(tts.spoken) == 1
