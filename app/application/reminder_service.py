"""Application service: proactive deadline reminders spoken while idle."""
from app.core.logger import logger
from app.domain.ports.clock import Clock
from app.domain.ports.memory import MemoryStore
from app.domain.ports.speech import TextToSpeech


class ReminderService:
    """Notifies the user (once per deadline) when a deadline falls due soon."""

    def __init__(self, store: MemoryStore, tts: TextToSpeech, clock: Clock) -> None:
        self._store = store
        self._tts = tts
        self._clock = clock
        self._notified: set[str] = set()

    def check_and_notify(self, minutes: int = 10) -> int:
        """Speak a reminder for each newly-due deadline; returns how many were spoken."""
        count = 0
        for deadline in self._store.deadlines_due_within(minutes):
            if deadline.id in self._notified:
                continue
            self._notified.add(deadline.id)
            logger.info(f"Reminder spoken: {deadline.title}")
            self._tts.speak(f"Boss, a reminder: {deadline.title} is due soon.")
            count += 1
        return count
