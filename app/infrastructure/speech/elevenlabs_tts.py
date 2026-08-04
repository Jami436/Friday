"""ElevenLabs adapter for the TextToSpeech port."""
from elevenlabs import ElevenLabs

from app.core.constants import TTS_SAMPLE_RATE
from app.core.exceptions import ConfigurationError
from app.domain.ports.audio import AudioOutput
from app.domain.ports.speech import TextToSpeech


class ElevenLabsTextToSpeech(TextToSpeech):
    """Synthesizes speech with ElevenLabs and streams it through an AudioOutput."""

    def __init__(
        self,
        api_key: str,
        audio_output: AudioOutput,
        voice_id: str = "",
    ) -> None:
        if not api_key:
            raise ConfigurationError(
                "ELEVENLABS_API_KEY is not set. Add it to the .env file. "
                "Get a key at https://elevenlabs.io/api-keys"
            )
        self._client = ElevenLabs(api_key=api_key)
        self._audio_output = audio_output
        self._voice_id = voice_id or self._resolve_voice_id()

    def _resolve_voice_id(self) -> str:
        voices = self._client.voices.get_all().voices
        british_female = next(
            (
                voice.voice_id
                for voice in voices
                if (
                    "british" in str(getattr(voice.labels, "accent", "")).lower()
                    and "female" in str(getattr(voice.labels, "gender", "")).lower()
                )
            ),
            None,
        )
        if british_female:
            return british_female
        if voices:
            return voices[0].voice_id
        raise ConfigurationError("No ElevenLabs voices available on this account.")

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        stream = self._client.text_to_speech.convert(
            voice_id=self._voice_id,
            text=text,
            output_format="pcm_24000",
        )
        self._audio_output.play(stream, sample_rate=TTS_SAMPLE_RATE)
