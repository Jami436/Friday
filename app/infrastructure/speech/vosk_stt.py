"""Vosk adapter for the SpeechToText port."""
import json

import numpy as np

from app.domain.ports.speech import SpeechToText
from app.infrastructure.speech.vosk_model import get_vosk_model


class VoskSpeechToText(SpeechToText):
    """Transcribes 16 kHz mono int16 PCM audio."""

    def __init__(self) -> None:
        from vosk import KaldiRecognizer

        self._recognizer = KaldiRecognizer(get_vosk_model(), 16000)

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        self._recognizer.AcceptWaveform(audio.tobytes())
        result = json.loads(self._recognizer.FinalResult())
        return result.get("text", "").strip()
