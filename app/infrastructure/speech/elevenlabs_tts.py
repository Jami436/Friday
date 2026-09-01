"""ElevenLabs adapter for the TextToSpeech port."""
from collections.abc import Iterator
from typing import Any, cast

from elevenlabs import ElevenLabs
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.constants import TTS_SAMPLE_RATE
from app.core.exceptions import ConfigurationError
from app.domain.ports.audio import AudioOutput
from app.domain.ports.speech import TextToSpeech


class ElevenLabsTextToSpeech(TextToSpeech):
    """Synthesizes speech with ElevenLabs and streams it through an AudioOutput.

    Transient network/HTTP failures are retried with exponential backoff; only
    a hard configuration error escapes immediately. Final fallbacks (Windows
    SAPI / console) are decided by the caller in the composition root.
    """

    def __init__(
        self,
        api_key: str,
        audio_output: AudioOutput,
        voice_id: str = "",
        *,
        stability: float | None = None,
        similarity_boost: float | None = None,
        max_retries: int = 3,
    ) -> None:
        if not api_key:
            raise ConfigurationError(
                "ELEVENLABS_API_KEY is not set. Add it to the .env file. "
                "Get a key at https://elevenlabs.io/api-keys"
            )
        self._client = ElevenLabs(api_key=api_key)
        self._audio_output = audio_output
        self._voice_id = voice_id or self._resolve_voice_id()
        self._stability = stability
        self._similarity_boost = similarity_boost
        self._speak_with_retry = retry(
            retry=retry_if_not_exception_type((ConfigurationError,)),
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
            reraise=True,
        )(self._speak_once)

    def _resolve_voice_id(self) -> str:
        voices = self._client.voices.get_all().voices
        british_female = next(
            (
                str(voice.voice_id)
                for voice in voices
                if (
                    "british" in str(getattr(voice.labels, "accent", "")).lower()
                    and "female" in str(getattr(voice.labels, "gender", "")).lower()
                )
            ),
            None,
        )
        if british_female is not None:
            return british_female
        if voices:
            return str(voices[0].voice_id)
        raise ConfigurationError("No ElevenLabs voices available on this account.")

    def _voice_settings(self) -> dict[str, Any]:
        settings: dict[str, Any] = {}
        if self._stability is not None:
            settings["stability"] = self._stability
        if self._similarity_boost is not None:
            settings["similarity_boost"] = self._similarity_boost
        return settings

    def _convert(self, text: str) -> Iterator[Any]:
        kwargs: dict[str, Any] = {
            "voice_id": self._voice_id,
            "text": text,
            "output_format": "pcm_24000",
        }
        voice_settings = self._voice_settings()
        if voice_settings:
            kwargs["voice_settings"] = voice_settings
        return cast(Iterator[Any], self._client.text_to_speech.convert(**kwargs))

    def _speak_once(self, text: str) -> None:
        if not text.strip():
            return
        stream = self._convert(text)
        self._audio_output.play(stream, sample_rate=TTS_SAMPLE_RATE)

    def speak(self, text: str) -> None:
        self._speak_with_retry(text)

    def cancel(self) -> None:
        """Stop any in-flight playback at the next chunk boundary."""
        self._audio_output.cancel()

    @property
    def voice_id(self) -> str:
        return self._voice_id
