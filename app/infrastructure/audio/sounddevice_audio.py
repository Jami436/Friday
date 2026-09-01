"""Sounddevice adapters for the AudioStream and AudioOutput ports."""
import contextlib
import queue
import threading

import numpy as np
import sounddevice as sd

from app.core.constants import AUDIO_BLOCK_SIZE, AUDIO_SAMPLE_RATE, TTS_SAMPLE_RATE


class SounddeviceMicrophone:
    """Implements AudioStream: a live mono int16 PCM microphone stream."""

    def __init__(self, device: int | None = None, sample_rate: int = AUDIO_SAMPLE_RATE) -> None:
        self._device = device
        self._sample_rate = sample_rate
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=200)
        self._stream: sd.InputStream | None = None
        self._stop = threading.Event()

    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            return
        with contextlib.suppress(queue.Full):
            self._queue.put_nowait(np.array(indata[:, 0], dtype=np.int16, copy=True))

    def __enter__(self) -> "SounddeviceMicrophone":
        self._stop = threading.Event()
        self._stream = sd.InputStream(
            samplerate=self._sample_rate,
            blocksize=AUDIO_BLOCK_SIZE,
            channels=1,
            dtype="int16",
            device=self._device,
            callback=self._callback,
        )
        self._stream.start()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def read_blocks(self):
        """Yield int16 blocks forever until close()."""
        while not self._stop.is_set():
            try:
                yield self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

    def close(self) -> None:
        self._stop.set()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


class SounddeviceAudioOutput:
    """Implements AudioOutput: plays raw mono int16 PCM to the speaker."""

    def __init__(self, device: int | None = None) -> None:
        self._device = device
        self._stop_event = threading.Event()

    def play(self, pcm_chunks, sample_rate: int = TTS_SAMPLE_RATE) -> None:
        self._stop_event.clear()
        with sd.OutputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            device=self._device,
        ) as stream:
            for chunk in pcm_chunks:
                if self._stop_event.is_set():
                    break
                if isinstance(chunk, bytes):
                    chunk = np.frombuffer(chunk, dtype=np.int16)
                stream.write(chunk)

    def cancel(self) -> None:
        """Request an in-flight ``play`` to stop at the next chunk boundary."""
        self._stop_event.set()
