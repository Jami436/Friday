"""Windows SAPI adapter for the TextToSpeech port (offline, no API key)."""
import win32com.client

from app.domain.ports.speech import TextToSpeech

_FEMALE_HINTS = ("zira", "hazel", "susan", "aria", "jenny", "libby", "sonia", "catherine", "emma")
_BRITISH_HINTS = ("en-gb", "en_gb")


class SystemSpeechTextToSpeech(TextToSpeech):
    """Speaks through the Windows SAPI5 voices via COM. Offline and dependency-free."""

    def __init__(self, voice_hint: str = "female") -> None:
        self._engine = win32com.client.Dispatch("SAPI.SpVoice")
        current_rate = self._engine.Rate
        self._engine.Rate = max(-10, current_rate - 2)
        self._engine.Voice = self._engine.GetVoices().Item(self._select_voice_index(voice_hint.lower()))

    def _select_voice_index(self, hint: str) -> int:
        voices = self._engine.GetVoices()
        if "british" in hint:
            for i in range(voices.Count):
                description = voices.Item(i).GetDescription().lower()
                if any(keyword in description for keyword in _BRITISH_HINTS):
                    return i
            return 0
        if "female" in hint:
            for i in range(voices.Count):
                description = voices.Item(i).GetDescription().lower()
                if any(keyword in description for keyword in _FEMALE_HINTS):
                    return i
            return 0
        return 0

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        self._engine.Speak(text)
