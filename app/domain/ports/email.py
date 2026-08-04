"""Port for reading the user's email."""
from typing import Protocol

from app.domain.entities.email import EmailMessage


class EmailProvider(Protocol):
    """Fetches recent inbox emails for summarization."""

    def fetch_recent(
        self,
        days: int = 3,
        limit: int = 15,
        unread_only: bool = True,
    ) -> list[EmailMessage]: ...
