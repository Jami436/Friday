import numpy as np

from app.infrastructure.audio.clap_detector import ClapDetector


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
