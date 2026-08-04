"""Domain entity: a dated deadline / reminder."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Deadline:
    id: str
    title: str
    due: str  # ISO date, YYYY-MM-DD
    time: str = ""  # optional HH:MM
    done: bool = False
    source: str = "voice"
    created: str = ""
