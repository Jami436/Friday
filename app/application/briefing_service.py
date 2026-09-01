"""Application service: assembles FRIDAY's working context and morning briefing."""
from app.domain.entities.email import EmailMessage
from app.domain.ports.clock import Clock
from app.domain.ports.email import EmailProvider
from app.domain.ports.memory import MemoryStore
from app.domain.services.time_format import format_now, time_of_day


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

    def _new_emails_since_last_seen(self) -> list[EmailMessage]:
        """Emails the user hasn't heard about yet, based on the last UID we surfaced."""
        emails = self._email.fetch_recent(days=3, limit=15)
        if not emails:
            return []
        last_seen = self._store.get_last_seen_email_id()
        if last_seen is None:
            return emails
        for index, message in enumerate(emails):
            if message.uid == last_seen:
                return emails[:index]
        return emails

    def _track_last_seen_email(self, emails: list[EmailMessage]) -> None:
        if emails:
            self._store.set_last_seen_email_id(emails[0].uid)

    def build_daily_context(self) -> str:
        """Authoritative daily-matters summary injected into the system prompt."""
        parts: list[str] = []

        tasks = self._store.pending_tasks()
        if tasks:
            parts.append("Pending tasks:")
            parts.extend(f"- {task.title}" for task in tasks)

        today = self._clock.now().date()
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
        today = now.date()

        parts = [f"Good {time_of_day(now)}, Boss. It's {format_now(now)}."]

        due_today = self._store.deadlines_due_on(today)
        if due_today:
            items = ", ".join(item.title for item in due_today)
            parts.append(f"You have {len(due_today)} deadline{'s' if len(due_today) != 1 else ''} today: {items}.")
        else:
            parts.append("Nothing is due today.")

        tasks = self._store.pending_tasks()
        if tasks:
            parts.append(f"You also have {len(tasks)} task{'s' if len(tasks) != 1 else ''} on your list.")

        new_emails = self._new_emails_since_last_seen()
        if new_emails:
            count = len(new_emails)
            parts.append(
                f"And there {'are' if count != 1 else 'is'} {count} new unread "
                f"email{'s' if count != 1 else ''} since you last checked."
            )
            parts.append(f"The most recent one is '{new_emails[0].subject}'.")
            self._track_last_seen_email(new_emails)

        parts.append("Ready when you are, Boss.")
        return " ".join(parts)
