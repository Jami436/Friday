"""Shared fakes for testing ports without real infrastructure."""
from datetime import datetime
from typing import Optional

import numpy as np

from app.domain.entities.conversation import ChatMessage
from app.domain.entities.email import EmailMessage
from app.domain.ports.ai import AIProvider
from app.domain.ports.clock import Clock
from app.domain.ports.speech import TextToSpeech, WakeEngine


class FakeAIProvider(AIProvider):
    """Returns scripted responses; can queue per-call replies."""

    def __init__(self, default: str = "Understood, Boss.", queue: Optional[list[str]] = None) -> None:
        self._default = default
        self._queue = list(queue or [])
        self.requests: list[str] = []

    def generate_response(self, prompt: str) -> str:
        self.requests.append(prompt)
        return self._queue.pop(0) if self._queue else self._default

    def chat(
        self,
        history: list[ChatMessage],
        system_instruction: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        self.requests.append(history[-1].text if history else "")
        return self._queue.pop(0) if self._queue else self._default


class FakeClock(Clock):
    def __init__(self, now: Optional[datetime] = None) -> None:
        self._now = now or datetime(2026, 8, 3, 19, 4)

    def now(self) -> datetime:
        return self._now


class FakeTTS(TextToSpeech):
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)


class FakeWakeEngine(WakeEngine):
    def __init__(self, reasons: Optional[list[str]] = None) -> None:
        self._reasons = list(reasons or ["clap"])
        self.idle_hook_calls = 0

    def wait_for_wake(self, idle_hook=None, idle_interval: float = 60.0) -> str:
        if idle_hook is not None:
            idle_hook()
            self.idle_hook_calls += 1
        return self._reasons.pop(0) if self._reasons else "clap"


class FakeEmailProvider:
    def __init__(self, messages: Optional[list[EmailMessage]] = None) -> None:
        self._messages = messages or []

    def fetch_recent(self, days: int = 3, limit: int = 15, unread_only: bool = True) -> list[EmailMessage]:
        return self._messages[:limit]


class FakeSTT:
    def __init__(self, texts: Optional[list[str]] = None) -> None:
        self._texts = list(texts or ["Hello, Boss."])

    def transcribe(self, audio: np.ndarray) -> str:
        return self._texts.pop(0) if self._texts else ""


class FakeVAD:
    def __init__(self, empty_on_call: Optional[list[bool]] = None) -> None:
        self._empty = list(empty_on_call or [False])

    def record_utterance(self, max_sec=None, silence_sec=None) -> np.ndarray:
        if self._empty.pop(0) if self._empty else False:
            return np.array([], dtype=np.int16)
        return np.zeros(1600, dtype=np.int16)
