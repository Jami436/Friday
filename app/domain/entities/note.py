"""Domain entity: a free-form note."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Note:
    id: str
    text: str
    created: str = ""
