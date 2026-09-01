"""Sounddevice adapter for the VoiceActivityDetector port."""
import collections

import numpy as np

from app.core.constants import AUDIO_BLOCK_SIZE, AUDIO_SAMPLE_RATE
from app.domain.ports.speech import VoiceActivityDetector
from app.infrastructure.audio.sounddevice_audio import SounddeviceMicrophone


def _rms(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(block, dtype=np.float64))))


class SounddeviceVoiceActivityDetector(VoiceActivityDetector):
    """Records one utterance, stopping after a configurable run of silence."""

    def __init__(
        self,
        device: int | None = None,
        default_max_sec: float = 12.0,
        default_silence_sec: float = 1.2,
    ) -> None:
        self._device = device
        self._default_max_sec = default_max_sec
        self._default_silence_sec = default_silence_sec

    def record_utterance(
        self,
        max_sec: float | None = None,
        silence_sec: float | None = None,
    ) -> np.ndarray:
        max_sec = max_sec or self._default_max_sec
        silence_sec = silence_sec or self._default_silence_sec
        required_silence = max(1, int(silence_sec * AUDIO_SAMPLE_RATE / AUDIO_BLOCK_SIZE))
        max_blocks = int(max_sec * AUDIO_SAMPLE_RATE / AUDIO_BLOCK_SIZE)

        with SounddeviceMicrophone(self._device) as mic:
            frames: list[np.ndarray] = []
            lead_in: collections.deque[np.ndarray] = collections.deque(maxlen=10)
            noise_floor = 200.0
            active = False
            silence_blocks = 0

            for blocks_seen, block in enumerate(mic.read_blocks(), start=1):
                rms_value = _rms(block)
                threshold = max(noise_floor * 3.0, 500.0)

                if not active:
                    if rms_value > threshold:
                        active = True
                        silence_blocks = 0
                        frames.extend(lead_in)
                        frames.append(block)
                    else:
                        noise_floor = 0.97 * noise_floor + 0.03 * rms_value
                        lead_in.append(block)
                        if blocks_seen >= max_blocks:
                            return np.array([], dtype=np.int16)
                else:
                    frames.append(block)
                    silence_blocks = silence_blocks + 1 if rms_value < threshold else 0
                    if silence_blocks >= required_silence or len(frames) >= max_blocks:
                        break

        if not frames:
            return np.array([], dtype=np.int16)
        return np.concatenate(frames)
