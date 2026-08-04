"""Speech adapters: Vosk (STT + keyword) and ElevenLabs/Console (TTS)."""

from app.infrastructure.speech.console_tts import ConsoleTextToSpeech
from app.infrastructure.speech.elevenlabs_tts import ElevenLabsTextToSpeech
from app.infrastructure.speech.vosk_keyword import VoskKeywordSpotter
from app.infrastructure.speech.vosk_stt import VoskSpeechToText

__all__ = [
    "ConsoleTextToSpeech",
    "ElevenLabsTextToSpeech",
    "VoskKeywordSpotter",
    "VoskSpeechToText",
]
