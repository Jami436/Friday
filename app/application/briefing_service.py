"""Application service: assembles FRIDAY's working context and morning briefing."""
from datetime import date

from app.core.logger import logger
from app.domain.entities.email import EmailMessage
from app.domain.ports.clock import Clock
from app.domain.ports.email import EmailProvider
from app.domain.ports.memory import MemoryStore
from app.domain.services.time_format import format_now


class BriefingService:
    """Builds the daily-matters context and the spoken morning briefing."""

    def __init__(self, store: MemoryStore, email: EmailProvider, clock: Clock) -> None:
        self._store = store
        self._email = email
        self._clock = clock

    def _email_lines(self, limit: int = 6) -> list[str]:
        emails = self._email.fetch_recent(days=3, limit=15)
        if not emails:
            return []
        lines = [f"Unread emails: {len(emails)}"]
        for message in emails[:limit]:
            lines.append(f"- {message.subject} (from {message.sender}, {message.date})")
        return lines

    def build_daily_context(self) -> str:
        """Authoritative daily-matters summary injected into the system prompt."""
        parts: list[str] = []

        tasks = self._store.pending_tasks()
        if tasks:
            parts.append("Pending tasks:")
            parts.extend(f"- {task.title}" for task in tasks)

        today = date.today()
        due_today = self._store.deadlines_due_on(today)
        if due_today:
            parts.append("Deadlines due TODAY:")
            for item in due_today:
                suffix = f" at {item.time}" if item.time else ""
                parts.append(f"- {item.title}{suffix}")

        upcoming = [d for d in self._store.upcoming_deadlines(6) if d.due != today.isoformat()]
        if upcoming:
            parts.append("Upcoming deadlines:")
            for item in upcoming:
                suffix = f" at {item.time}" if item.time else ""
                parts.append(f"- {item.title} ({item.due}){suffix}")

        notes = self._store.notes(3)
        if notes:
            parts.append("Recent notes:")
            parts.extend(f"- {note.text}" for note in notes)

        parts.extend(self._email_lines())

        return "\n".join(parts) if parts else "No pending daily matters."

    def build_morning_briefing(self) -> str:
        """Spoken text for the first wake of the day."""
        now = self._clock.now()
        today = date.today()

        greeting = "morning" if now.hour < 12 else "afternoon"
        parts = [f"Good {greeting}, Boss. It's {format_now(now)}."]

        due_today = self._store.deadlines_due_on(today)
        if due_today:
            items = ", ".join(item.title for item in due_today)
            parts.append(f"You have {len(due_today)} deadline{'s' if len(due_today) != 1 else ''} today: {items}.")
        else:
            parts.append("Nothing is due today.")

        tasks = self._store.pending_tasks()
        if tasks:
            parts.append(f"You also have {len(tasks)} task{'s' if len(tasks) != 1 else ''} on your list.")

        emails = self._email.fetch_recent(days=3, limit=15)
        if emails:
            count = len(emails)
            parts.append(f"And there {'are' if count != 1 else 'is'} {count} unread email{'s' if count != 1 else ''} in your inbox.")
            parts.append(f"The most recent one is '{emails[0].subject}'.")

        parts.append("Ready when you are, Boss.")
        return " ".join(parts)
