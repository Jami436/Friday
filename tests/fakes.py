"""Shared fakes for testing ports without real infrastructure."""
from datetime import datetime
from threading import Event

import numpy as np

from app.domain.entities.conversation import ChatMessage
from app.domain.entities.email import EmailMessage
from app.domain.ports.ai import AIProvider
from app.domain.ports.clock import Clock
from app.domain.ports.security import PassphraseStore, SpeakerVerifier
from app.domain.ports.speech import TextToSpeech, WakeEngine


class FakeAIProvider(AIProvider):
    """Returns scripted responses; can queue per-call replies."""

    def __init__(self, default: str = "Understood, Boss.", queue: list[str] | None = None) -> None:
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
    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 8, 3, 19, 4)

    def now(self) -> datetime:
        return self._now


class FakeTTS(TextToSpeech):
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.cancelled: Event = Event()

    def speak(self, text: str) -> None:
        self.spoken.append(text)

    def cancel(self) -> None:
        self.cancelled.set()


class FakeWakeEngine(WakeEngine):
    def __init__(self, reasons: list[str] | None = None, idle_returns: list[bool] | None = None) -> None:
        self._reasons = list(reasons or ["clap"])
        self.idle_hook_calls = 0
        self.closed = Event()
        self._idle_returns = list(idle_returns or [])

    def close(self) -> None:
        self.closed.set()

    def wait_for_wake(self, idle_hook=None, idle_interval: float = 60.0) -> str:
        if self._idle_returns and self._idle_returns.pop(0) and idle_hook is not None:
            idle_hook()
            self.idle_hook_calls += 1
        return self._reasons.pop(0) if self._reasons else "clap"


class FakeEmailProvider:
    def __init__(self, messages: list[EmailMessage] | None = None) -> None:
        self._messages = messages or []

    def fetch_recent(self, days: int = 3, limit: int = 15, unread_only: bool = True) -> list[EmailMessage]:
        return self._messages[:limit]


class FakeSTT:
    def __init__(self, texts: list[str] | None = None) -> None:
        self._texts = list(texts or ["Hello, Boss."])

    def transcribe(self, audio: np.ndarray) -> str:
        return self._texts.pop(0) if self._texts else ""


class FakeVAD:
    def __init__(self, empty_on_call: list[bool] | None = None) -> None:
        self._empty = list(empty_on_call or [False])

    def record_utterance(self, max_sec=None, silence_sec=None) -> np.ndarray:
        if self._empty.pop(0) if self._empty else False:
            return np.array([], dtype=np.int16)
        return np.zeros(1600, dtype=np.int16)


class FakeSpeakerVerifier(SpeakerVerifier):
    """Scripted speaker verifier; controls the returned similarity score."""

    def __init__(self, score: float = 0.9, enrolled: bool = True) -> None:
        self._score = score
        self._enrolled = enrolled
        self.enrolled_samples: list[np.ndarray] = []

    def is_enrolled(self) -> bool:
        return self._enrolled

    def enroll(self, samples: list[np.ndarray]) -> None:
        self._enrolled = True
        self.enrolled_samples.extend(samples)

    def verify(self, audio: np.ndarray) -> float:
        return self._score


class FakePassphraseStore(PassphraseStore):
    def __init__(self, passphrase: str = "") -> None:
        self._passphrase = passphrase

    def get(self) -> str:
        return self._passphrase

    def set(self, passphrase: str) -> None:
        self._passphrase = passphrase
