"""Clap detection: a WakeDetector that spots a burst of claps by energy analysis."""
import time

import numpy as np

from app.domain.ports.speech import WakeDetector


def _rms(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(block, dtype=np.float64))))


class ClapDetector(WakeDetector):
    """Detects >= min_count sharp transients (claps) within a rolling window."""

    def __init__(
        self,
        min_count: int = 2,
        window_sec: float = 1.8,
        trailing_silence_sec: float = 0.45,
        clock=None,
    ) -> None:
        self._min_count = min_count
        self._window_sec = window_sec
        self._trailing_silence_sec = trailing_silence_sec
        self._clock = clock or time.monotonic
        self._noise_floor = 200.0
        self._last_rms = 0.0
        self._claps: list[float] = []

    def _reset_noise(self, rms_value: float) -> None:
        if self._last_rms > 0:
            if rms_value < self._noise_floor * 4:
                self._noise_floor = 0.96 * self._noise_floor + 0.04 * rms_value
        else:
            self._noise_floor = max(self._noise_floor, rms_value)

    def feed(self, block: np.ndarray) -> bool:
        rms_value = _rms(block)
        now = self._clock()
        threshold = max(self._noise_floor * 6.0, 900.0)

        is_rise = self._last_rms < threshold * 0.7 and rms_value > threshold
        self._last_rms = rms_value
        self._reset_noise(rms_value)

        if is_rise:
            self._claps.append(now)

        self._claps = [t for t in self._claps if now - t <= self._window_sec]

        if (
            len(self._claps) >= self._min_count
            and now - self._claps[-1] > self._trailing_silence_sec
        ):
            self._claps.clear()
            self._noise_floor = 200.0
            return True

        return False
