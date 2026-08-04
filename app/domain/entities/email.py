"""Domain entity: an email message surfaced by an EmailProvider."""
from dataclasses import dataclass


@dataclass(frozen=True)
class EmailMessage:
    uid: str
    subject: str
    sender: str
    date: str
    snippet: str
