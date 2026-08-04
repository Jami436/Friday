"""Application service: extract tasks/deadlines/notes from a voice request."""
import json
import re
from datetime import date

from app.core.logger import logger
from app.domain.ports.ai import AIProvider
from app.domain.ports.clock import Clock
from app.domain.services.clock import SystemClock

EXTRACTOR_PROMPT = """You are a strict structured-data extractor. Today's date is {today}.

Read the user's request and detect ONLY explicit asks to:
- set or add a deadline / reminder / "remind me"  -> type "deadline", fields: title (str), due (YYYY-MM-DD or null if not given), time (HH:MM or null)
- add a task / to-do / "put it on my list"        -> type "task", field: title
- remember / note something                       -> type "note", field: text

Rules:
- If a date is given relative to today (e.g. "tomorrow", "next monday", "in 3 days"), resolve it to an absolute YYYY-MM-DD using today's date.
- Do NOT extract requests to read, list, summarize or cancel things.
- Return ONLY a JSON array of actions, or [] if nothing qualifies. No prose, no markdown fences.
"""

# Cheap pre-filter: if the request contains none of these cues, we skip the
# expensive LLM extraction call entirely. Intentionally generous so real
# requests are never missed; it only costs an AI round-trip on false positives.
_ACTION_HINTS = (
    # action verbs
    "remind",
    "reminder",
    "remember",
    "don't forget",
    "deadline",
    "due",
    "task",
    "to-do",
    "todo",
    "add",
    "create",
    "make",
    "set up",
    "set a",
    "set an",
    "schedule",
    "book",
    "plan",
    "note",
    "write down",
    "jot",
    "save",
    "record",
    # date/time references (implicit deadlines like "call mom tomorrow")
    "tomorrow",
    "tonight",
    "today",
    "next",
    "weekend",
    "this week",
    "next week",
    "o'clock",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "on the",
    "at ",
    "by ",
    "in ",
)

_HINT_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(hint) for hint in _ACTION_HINTS) + r")",
    re.IGNORECASE,
)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class MemoryExtractor:
    """Structured-action extraction; the provider is injected for testability."""

    def __init__(self, ai: AIProvider, clock: Clock | None = None) -> None:
        self._ai = ai
        self._clock = clock or SystemClock()

    def _should_extract(self, user_text: str) -> bool:
        return bool(_HINT_RE.search(user_text))

    def extract(self, user_text: str) -> list[dict]:
        if not self._should_extract(user_text):
            return []
        today: date = self._clock.now().date()
        prompt = EXTRACTOR_PROMPT.format(today=today.isoformat())
        raw = self._ai.generate_response(prompt + f"\nUser request: {user_text}").strip()
        fence = _FENCE_RE.search(raw)
        if fence:
            raw = fence.group(1).strip()
        try:
            actions = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Memory extractor returned non-JSON: {raw!r}")
            return []
        if not isinstance(actions, list):
            return []
        return [action for action in actions if isinstance(action, dict) and "type" in action]
