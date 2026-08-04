"""Ports for low-level audio capture and playback."""
from typing import Iterator, Protocol

import numpy as np


class AudioStream(Protocol):
    """A live microphone stream yielding mono int16 PCM blocks."""

    def __enter__(self) -> "AudioStream": ...

    def __exit__(self, *exc) -> None: ...

    def read_blocks(self) -> Iterator[np.ndarray]: ...

    def close(self) -> None: ...


class AudioOutput(Protocol):
    """Plays raw mono int16 PCM to the default output device."""

    def play(self, pcm_chunks, sample_rate: int) -> None: ...
