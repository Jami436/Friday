"""Application service: verify the person speaking is the local machine's owner."""
import re

from app.core.logger import logger
from app.domain.ports.clock import Clock
from app.domain.ports.security import PassphraseStore, SpeakerVerifier
from app.domain.ports.speech import SpeechToText, TextToSpeech, VoiceActivityDetector

SECURITY_MODE_VOICE = "voice"
SECURITY_MODE_PASSPHRASE = "passphrase"
SECURITY_MODE_BOTH = "both"

_PHRASE_NORMALIZE_RE = re.compile(r"[^a-z0-9 ]+")
_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    text = _PHRASE_NORMALIZE_RE.sub("", text.lower())
    return _WS_RE.sub(" ", text).strip()


class AccessControlService:
    """Gates FRIDAY behind owner verification (voice and/or passphrase).

    Voice similarity uses the local enrollment profile; the passphrase comes
    from the local passphrase store or the configured default. When security
    is disabled, ``authorize`` always grants access.
    """

    def __init__(
        self,
        verifier: SpeakerVerifier,
        passphrase_store: PassphraseStore,
        vad: VoiceActivityDetector,
        stt: SpeechToText,
        tts: TextToSpeech,
        clock: Clock,
        *,
        enabled: bool,
        mode: str,
        threshold: float,
        passphrase: str,
        owner_name: str,
    ) -> None:
        self._verifier = verifier
        self._passphrase_store = passphrase_store
        self._vad = vad
        self._stt = stt
        self._tts = tts
        self._clock = clock
        self._enabled = enabled
        self._mode = mode
        self._threshold = threshold
        self._passphrase = passphrase
        self._owner_name = owner_name

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _verify_voice(self) -> bool:
        self._tts.speak("Voice check, Boss.")
        audio = self._vad.record_utterance()
        score = self._verifier.verify(audio)
        logger.info(f"Speaker similarity: {score:.2f}")
        return score >= self._threshold

    def _verify_passphrase(self) -> bool:
        expected = self._passphrase_store.get() or self._passphrase
        if not expected:
            logger.warning("Passphrase not set; passphrase verification cannot succeed.")
            return False
        self._tts.speak("Access passphrase, Boss?")
        audio = self._vad.record_utterance()
        spoken = self._stt.transcribe(audio).strip()
        logger.info(f"Passphrase attempt (normalized): {_normalize(spoken)!r}")
        return _normalize(spoken) == _normalize(expected)

    def authorize(self) -> bool:
        """Prompt the speaker to prove they are the owner; returns True if granted."""
        if not self._enabled:
            return True
        if not self._verifier.is_enrolled() and self._mode == SECURITY_MODE_VOICE:
            logger.warning("No voice profile enrolled; security mode is voice-only.")
            self._tts.speak("No owner profile enrolled yet, Boss. Please run the enrollment.")
            return False

        if self._mode == SECURITY_MODE_VOICE:
            granted = self._verify_voice()
        elif self._mode == SECURITY_MODE_PASSPHRASE:
            granted = self._verify_passphrase()
        else:  # both
            granted = self._verify_voice()
            if not granted:
                self._tts.speak("Voice not recognized. Passphrase, Boss?")
                granted = self._verify_passphrase()

        if granted:
            logger.info(f"Owner verified ({self._owner_name}).")
            self._tts.speak(f"Welcome back, {self._owner_name}.")
            return True
        self._tts.speak("Access denied, Boss.")
        return False
