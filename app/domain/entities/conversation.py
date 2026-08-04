"""Domain entity: one turn in an assistant conversation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "user" | "model" | "system"
    text: str
