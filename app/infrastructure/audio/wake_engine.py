"""Wake engine adapter: combines clap + keyword detection on the live mic."""
import time
from typing import Callable

from app.domain.ports.audio import AudioStream
from app.domain.ports.speech import WakeDetector, WakeEngine


class SounddeviceWakeEngine(WakeEngine):
    """Implements WakeEngine: blocks until a clap or keyword wakes FRIDAY."""

    def __init__(
        self,
        stream_factory: Callable[[], AudioStream],
        clap_detector_factory: Callable[[], WakeDetector],
        keyword_spotter_factory: Callable[[], WakeDetector],
    ) -> None:
        self._stream_factory = stream_factory
        self._clap_factory = clap_detector_factory
        self._keyword_factory = keyword_spotter_factory

    def wait_for_wake(
        self,
        idle_hook: Callable[[], None] | None = None,
        idle_interval: float = 60.0,
    ) -> str:
        stream = self._stream_factory().__enter__()
        clap = self._clap_factory()
        keyword = self._keyword_factory()
        last_hook = time.monotonic()
        try:
            for block in stream.read_blocks():
                now = time.monotonic()
                if idle_hook is not None and now - last_hook >= idle_interval:
                    stream.close()
                    stream = self._stream_factory().__enter__()
                    keyword = self._keyword_factory()
                    last_hook = time.monotonic()
                    continue
                if clap.feed(block):
                    return "clap"
                if keyword.feed(block):
                    return "keyword"
        finally:
            stream.close()
