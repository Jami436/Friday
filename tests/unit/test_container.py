"""Verify the Composition Root wires the application together with overrides."""
import pytest

from app.container import build_container
from app.core.config import Settings
from app.infrastructure.persistence.sqlite_store import SqliteMemoryStore
from tests.fakes import FakeAIProvider, FakeClock, FakeEmailProvider, FakeSTT, FakeTTS, FakeVAD, FakeWakeEngine


@pytest.fixture
def container(tmp_path):
    return build_container(
        settings=Settings(gemini_api_key="test-key-that-is-long-enough-0000", _env_file=None),
        ai=FakeAIProvider(),
        store=SqliteMemoryStore(tmp_path / "test.db"),
        email=FakeEmailProvider(),
        tts=FakeTTS(),
        stt=FakeSTT(),
        vad=FakeVAD(),
        wake_engine=FakeWakeEngine(),
    )


def test_container_exposes_wired_services(container):
    assert container.assistant is not None
    assert container.briefing is not None
    assert container.conversation is not None
    assert container.reminders is not None


def test_container_assistant_round_trip(container):
    reply = container.assistant.respond("Hello")
    assert reply


def test_container_store_persists(container, tmp_path):
    container.store.add_task("Test task")
    assert container.store.pending_tasks()[0].title == "Test task"
