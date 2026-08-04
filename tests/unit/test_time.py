from datetime import datetime

from app.domain.services.time_format import format_now, ordinal, time_of_day


def test_format_now_includes_ampm():
    now = datetime(2026, 8, 3, 19, 4)
    assert format_now(now) == "Monday, August 3rd, 7:04 PM"


def test_format_now_am():
    now = datetime(2026, 1, 1, 8, 5)
    assert "8:05 AM" in format_now(now)


def test_ordinal_edge_cases():
    for day, expected in [(1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"), (11, "11th"), (21, "21st"), (22, "22nd")]:
        assert ordinal(day) == expected


def test_time_of_day_periods():
    assert time_of_day(datetime(2026, 8, 3, 9, 0)) == "morning"
    assert time_of_day(datetime(2026, 8, 3, 14, 0)) == "afternoon"
    assert time_of_day(datetime(2026, 8, 3, 18, 0)) == "evening"
    assert time_of_day(datetime(2026, 8, 3, 23, 0)) == "night"
