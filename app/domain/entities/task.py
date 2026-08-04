"""Domain entity: a to-do task."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    done: bool = False
    created: str = ""
