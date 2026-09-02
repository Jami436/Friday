import threading
import time

import numpy as np

from app.infrastructure.audio.clap_detector import ClapDetector
from app.infrastructure.audio.wake_engine import SounddeviceWakeEngine


class FakeClock:
    def __init__(self, step: float = 0.1) -> None:
        self.t = 0.0
        self.step = step

    def __call__(self) -> float:
        self.t += self.step
        return self.t


def _quiet(rng: np.random.Generator) -> np.ndarray:
    return rng.integers(-90, 90, 1600).astype(np.int16)


def _loud(rng: np.random.Generator) -> np.ndarray:
    return (rng.integers(-100, 100, 1600) + 8000).astype(np.int16)


def _stream(rng, n_quiet_before, *loud_positions, n_quiet_after=12):
    total = n_quiet_before + len(loud_positions) + n_quiet_after
    blocks = [_quiet(rng) for _ in range(total)]
    for position in loud_positions:
        blocks[position] = _loud(rng)
    return blocks


def test_two_claps_in_window_trigger():
    rng = np.random.default_rng(0)
    det = ClapDetector(clock=FakeClock())
    blocks = _stream(rng, 20, 20, 26)
    fired_at = -1
    for i, block in enumerate(blocks):
        if det.feed(block):
            fired_at = i
            break
    assert fired_at == 31  # second clap + trailing silence


def test_single_clap_does_not_trigger():
    rng = np.random.default_rng(0)
    det = ClapDetector(clock=FakeClock())
    blocks = _stream(rng, 20, 20)
    assert not any(det.feed(b) for b in blocks)


def test_claps_outside_window_do_not_trigger():
    rng = np.random.default_rng(0)
    det = ClapDetector(clock=FakeClock())
    blocks = _quiet(rng) * 20 + [_loud(rng)] + _quiet(rng) * 30 + [_loud(rng)] + _quiet(rng) * 30
    assert not any(det.feed(b) for b in blocks)


class _FakeStream:
    """A controllable infinite stream that emits blocks until signalled to stop."""

    def __init__(self, blocks):
        self._blocks = list(blocks)
        self._stop = False
        self.closes = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def read_blocks(self):
        while not self._stop:
            for block in self._blocks:
                if self._stop:
                    return
                yield block

    def close(self):
        self.closes += 1
        self._stop = True


class _NeverDetect:
    def feed(self, block):
        return False


def test_wake_engine_reenables_after_close():
    """After close() (used to stop a conversation's interrupt monitor), the next
    wait_for_wake must block normally again instead of returning immediately."""
    quiet = (np.zeros(1600, dtype=np.int16),)
    engine = SounddeviceWakeEngine(
        stream_factory=lambda: _FakeStream(quiet),
        clap_detector_factory=lambda: _NeverDetect(),
        keyword_spotter_factory=lambda: _NeverDetect(),
    )

    def _blocking_wait():
        return engine.wait_for_wake(idle_interval=60.0)

    first_result = []
    first = threading.Thread(target=lambda: first_result.append(_blocking_wait()))
    first.start()
    time.sleep(0.05)
    engine.close()  # signal the first wait to exit
    first.join(timeout=1.0)
    assert first_result == [""]

    # The next wait must block again (the stop event was cleared by the fix);
    # if it returned immediately the whole idle loop would spin.
    second = threading.Thread(target=_blocking_wait)
    second.start()
    time.sleep(0.1)
    assert second.is_alive()  # still blocking = wake detection is active
    engine.close()  # unblock so the thread can end
    second.join(timeout=1.0)
    assert not second.is_alive()
