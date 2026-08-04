"""Domain service: time-aware formatting used by the FRIDAY persona."""
from datetime import datetime


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{'st' if n % 10 == 1 else 'nd' if n % 10 == 2 else 'rd' if n % 10 == 3 else 'th'}"


def format_now(now: datetime | None = None) -> str:
    """'Monday, August 3rd, 7:04 PM' — always includes AM/PM."""
    now = now or datetime.now()
    time_str = now.strftime("%I:%M %p").lstrip("0")
    return now.strftime("%A, %B ") + ordinal(now.day) + ", " + time_str


def time_of_day(now: datetime | None = None) -> str:
    """Returns 'morning', 'afternoon', 'evening' or 'night' based on AM/PM."""
    now = now or datetime.now()
    hour = now.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"
