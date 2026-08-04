"""Application service: the wake-to-idle conversation loop."""
from app.application.assistant_service import AssistantService
from app.core.constants import GOODBYE_HINTS, WAKE_WORD_ONLY
from app.core.logger import logger
from app.domain.ports.clock import Clock
from app.domain.ports.speech import SpeechToText, TextToSpeech, VoiceActivityDetector


class ConversationService:
    """Drives one wake-to-idle session: listen, think, speak."""

    def __init__(
        self,
        assistant: AssistantService,
        tts: TextToSpeech,
        stt: SpeechToText,
        vad: VoiceActivityDetector,
        clock: Clock,
    ) -> None:
        self._assistant = assistant
        self._tts = tts
        self._stt = stt
        self._vad = vad
        self._clock = clock

    @staticmethod
    def _is_goodbye(text: str) -> bool:
        lower = text.lower()
        return any(hint in lower for hint in GOODBYE_HINTS)

    def run(self) -> None:
        self._assistant.reset_history()
        self._tts.speak("Yes, Boss?")

        empty_strikes = 0
        while True:
            audio = self._vad.record_utterance()

            if audio.size == 0:
                empty_strikes += 1
                if empty_strikes >= 2:
                    logger.info("Conversation idle; returning to wake mode.")
                    return
                continue
            empty_strikes = 0

            text = self._stt.transcribe(audio).strip()
            if not text:
                continue
            logger.info(f"[Boss] {text}")

            if text.lower().strip() in WAKE_WORD_ONLY:
                continue

            if self._is_goodbye(text):
                self._tts.speak("Right away, Boss.")
                return

            reply = self._assistant.respond(text)
            if reply.text:
                self._tts.speak(reply.text)
            for confirmation in reply.confirmations:
                self._tts.speak(confirmation)
