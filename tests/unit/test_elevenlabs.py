"""Tests for the ElevenLabs TTS adapter using a fake client and output."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.core.exceptions import ConfigurationError
from app.infrastructure.speech.elevenlabs_tts import ElevenLabsTextToSpeech


class FakeVoice:
    def __init__(self, voice_id, labels=None) -> None:
        self.voice_id = voice_id
        self.labels = labels or {}


class FakeTTSAPI:
    def __init__(self, streams) -> None:
        self._streams = list(streams)
        self.calls: list[dict] = []

    def convert(self, **kwargs):
        self.calls.append(kwargs)
        return self._streams.pop(0) if self._streams else []


class FakeVoicesAPI:
    def __init__(self, voices) -> None:
        self.voices = voices

    def get_all(self):
        return self


class FakeClient:
    def __init__(self, streams=None, voices=None) -> None:
        self.text_to_speech = FakeTTSAPI(streams or [])
        self.voices = FakeVoicesAPI(voices or [])


class FakeAudioOutput:
    def __init__(self) -> None:
        self.played: list[tuple] = []
        self.cancelled = False

    def play(self, pcm_chunks, sample_rate: int):
        self.played.append((list(pcm_chunks), sample_rate))

    def cancel(self) -> None:
        self.cancelled = True


def _make_tts(voice_id="abc", **kwargs):
    client = FakeClient()
    tts = ElevenLabsTextToSpeech(api_key="sk-test", audio_output=FakeAudioOutput(), voice_id=voice_id, **kwargs)
    tts._client = client
    return tts, client


def test_missing_api_key_raises():
    with pytest.raises(ConfigurationError):
        ElevenLabsTextToSpeech(api_key="", audio_output=FakeAudioOutput())


def test_auto_resolves_voice_when_none_given():
    voices = [
        FakeVoice("v1", SimpleNamespace(accent="american", gender="male")),
        FakeVoice("v2", SimpleNamespace(accent="british", gender="female")),
    ]
    with patch("app.infrastructure.speech.elevenlabs_tts.ElevenLabs", return_value=FakeClient(voices=voices)):
        tts = ElevenLabsTextToSpeech(api_key="sk-test", audio_output=FakeAudioOutput())
    assert tts.voice_id == "v2"


def test_speak_passes_voice_settings_and_plays():
    audio = FakeAudioOutput()
    tts, client = _make_tts(voice_id="abc", stability=0.5, similarity_boost=0.3)
    tts._audio_output = audio
    tts.speak("Hello Boss")
    assert client.text_to_speech.calls[0]["voice_id"] == "abc"
    assert client.text_to_speech.calls[0]["voice_settings"] == {"stability": 0.5, "similarity_boost": 0.3}
    assert audio.played[0][0] == []


def test_speak_omits_settings_when_not_configured():
    audio = FakeAudioOutput()
    tts, client = _make_tts(voice_id="abc")
    tts._audio_output = audio
    tts.speak("Hi")
    assert "voice_settings" not in client.text_to_speech.calls[0]


def test_cancel_delegates_to_audio_output():
    audio = FakeAudioOutput()
    tts, _ = _make_tts(voice_id="abc")
    tts._audio_output = audio
    tts.cancel()
    assert audio.cancelled is True


def test_retries_transient_error_then_succeeds():
    def ok_stream():
        yield b"pcmdata"

    client = FakeClient()
    calls = {"n": 0}

    def convert_impl(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("boom")
        return ok_stream()

    client.text_to_speech.convert = convert_impl
    audio = FakeAudioOutput()
    tts = ElevenLabsTextToSpeech(api_key="sk-test", audio_output=audio, voice_id="abc")
    tts._client = client
    tts.speak("Hello")
    assert calls["n"] == 2
    assert audio.played[0][0] == [b"pcmdata"]


def test_speak_skips_empty_text():
    audio = FakeAudioOutput()
    tts, client = _make_tts(voice_id="abc")
    tts._audio_output = audio
    tts.speak("   ")
    assert client.text_to_speech.calls == []
    assert audio.played == []
