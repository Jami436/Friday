"""Port for time. Injected so time-dependent logic is testable."""
from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...
