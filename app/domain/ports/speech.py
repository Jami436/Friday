"""Ports for the voice pipeline: wake, VAD, STT and TTS."""
from collections.abc import Callable
from typing import Protocol

import numpy as np


class WakeDetector(Protocol):
    """Analyzes one audio block; returns True when the wake condition is met."""

    def feed(self, block: np.ndarray) -> bool: ...


class VoiceActivityDetector(Protocol):
    """Records a single utterance from the microphone until trailing silence."""

    def record_utterance(
        self,
        max_sec: float | None = None,
        silence_sec: float | None = None,
    ) -> np.ndarray: ...


class SpeechToText(Protocol):
    """Transcribes 16 kHz mono int16 PCM audio to text."""

    def transcribe(self, audio: np.ndarray) -> str: ...


class TextToSpeech(Protocol):
    """Synthesizes text and plays it through the speaker."""

    def speak(self, text: str) -> None: ...

    def cancel(self) -> None:
        """Best-effort immediate stop of any in-flight ``speak`` call."""
        ...


class WakeEngine(Protocol):
    """Blocks until woken, returning the wake reason ('clap' | 'keyword')."""

    def wait_for_wake(
        self,
        idle_hook: Callable[[], None] | None = None,
        idle_interval: float = 60.0,
    ) -> str: ...

    def close(self) -> None:
        """Best-effort request to stop any in-flight ``wait_for_wake``."""
        ...
