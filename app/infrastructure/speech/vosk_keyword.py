"""Vosk-based keyword spotter: a WakeDetector for the 'Friday' wake word."""
import json

import numpy as np

from app.core.constants import WAKE_KEYWORDS
from app.domain.ports.speech import WakeDetector
from app.infrastructure.speech.vosk_model import get_vosk_model


class VoskKeywordSpotter(WakeDetector):
    """Listens for a configured keyword using the offline Vosk recognizer."""

    def __init__(self, keywords: tuple[str, ...] = WAKE_KEYWORDS) -> None:
        from vosk import KaldiRecognizer

        self._keywords = keywords
        self._recognizer = KaldiRecognizer(get_vosk_model(), 16000)

    def feed(self, block: np.ndarray) -> bool:
        if not self._recognizer.AcceptWaveform(block.tobytes()):
            partial = self._recognizer.PartialResult()
            try:
                text = json.loads(partial).get("partial", "").strip().lower()
            except (ValueError, AttributeError):
                return False
            if text and any(keyword in text for keyword in self._keywords):
                return True
        return False
