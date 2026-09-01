"""Application service: the wake-to-idle conversation loop."""
import threading

from app.application.assistant_service import AssistantService
from app.core.constants import GOODBYE_HINTS, WAKE_WORD_ONLY
from app.core.logger import logger
from app.domain.ports.clock import Clock
from app.domain.ports.speech import SpeechToText, TextToSpeech, VoiceActivityDetector, WakeEngine


class ConversationService:
    """Drives one wake-to-idle session: listen, think, speak.

    When a ``wake_engine`` is supplied, speech is interruptible: a fresh wake
    (clap or saying "Friday") while FRIDAY is talking cancels the playback so
    the next utterance is captured immediately.
    """

    def __init__(
        self,
        assistant: AssistantService,
        tts: TextToSpeech,
        stt: SpeechToText,
        vad: VoiceActivityDetector,
        clock: Clock,
        wake_engine: WakeEngine | None = None,
    ) -> None:
        self._assistant = assistant
        self._tts = tts
        self._stt = stt
        self._vad = vad
        self._clock = clock
        self._wake_engine = wake_engine

    @staticmethod
    def _is_goodbye(text: str) -> bool:
        lower = text.lower()
        return any(hint in lower for hint in GOODBYE_HINTS)

    def speak(self, text: str) -> bool:
        """Speak ``text``; returns True if playback was interrupted by a wake."""
        if not text.strip():
            return False
        if self._wake_engine is None:
            self._tts.speak(text)
            return False

        interrupted = threading.Event()
        wake_engine = self._wake_engine

        def _interrupt_monitor() -> None:
            try:
                if wake_engine.wait_for_wake(idle_interval=0.08):
                    interrupted.set()
                    self._tts.cancel()
            except Exception:  # noqa: BLE001 - interruption is best-effort
                pass

        monitor = threading.Thread(target=_interrupt_monitor, daemon=True)
        monitor.start()
        try:
            self._tts.speak(text)
        finally:
            self._wake_engine.close()
        monitor.join(timeout=2.0)
        return interrupted.is_set()

    def run(self) -> None:
        self._assistant.reset_history()
        if self.speak("Yes, Boss?"):
            return

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
                self.speak("Right away, Boss.")
                return

            reply = self._assistant.respond(text)
            if reply.text:
                if self.speak(reply.text):
                    continue
            elif not reply.confirmations:
                self.speak("I'm sorry, Boss, I didn't quite catch that.")
            for confirmation in reply.confirmations:
                if self.speak(confirmation):
                    break
