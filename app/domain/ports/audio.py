"""Ports for low-level audio capture and playback."""
from collections.abc import Iterator
from typing import Protocol

import numpy as np


class AudioStream(Protocol):
    """A live microphone stream yielding mono int16 PCM blocks."""

    def __enter__(self) -> "AudioStream": ...

    def __exit__(
        self, exc_type: object, exc_val: object, exc_tb: object
    ) -> None: ...

    def read_blocks(self) -> Iterator[np.ndarray]: ...

    def close(self) -> None: ...


class AudioOutput(Protocol):
    """Plays raw mono int16 PCM to the default output device."""

    def play(self, pcm_chunks: Iterator[np.ndarray], sample_rate: int) -> None: ...

    def cancel(self) -> None:
        """Best-effort immediate stop of any in-flight ``play`` call."""
        ...
