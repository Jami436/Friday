"""Audio adapters: sounddevice capture/playback, clap detection, VAD and wake engine."""

from app.infrastructure.audio.clap_detector import ClapDetector
from app.infrastructure.audio.sounddevice_audio import (
    SounddeviceAudioOutput,
    SounddeviceMicrophone,
)
from app.infrastructure.audio.vad import SounddeviceVoiceActivityDetector
from app.infrastructure.audio.wake_engine import SounddeviceWakeEngine

__all__ = [
    "ClapDetector",
    "SounddeviceAudioOutput",
    "SounddeviceMicrophone",
    "SounddeviceVoiceActivityDetector",
    "SounddeviceWakeEngine",
]
