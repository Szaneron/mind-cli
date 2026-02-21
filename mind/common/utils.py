# Common utilities: date parsing and timezone helpers
from datetime import date as dt_date
from datetime import datetime, time
from zoneinfo import ZoneInfo

WARSAW_TZ = ZoneInfo("Europe/Warsaw")


def utc_iso_to_warsaw_local(utc_time_str: str) -> datetime:
    """Convert UTC ISO string (e.g. '2026-02-20T08:00:00Z') to Warsaw local datetime."""
    utc_dt = datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))
    return utc_dt.astimezone(WARSAW_TZ)


def day_range_utc(date: dt_date) -> tuple[str, str]:
    """Return start and end UTC ISO strings for a full day in Warsaw timezone."""
    start = datetime.combine(date, time.min, tzinfo=WARSAW_TZ).astimezone(
        ZoneInfo("UTC")
    )
    end = datetime.combine(date, time.max, tzinfo=WARSAW_TZ).astimezone(ZoneInfo("UTC"))
    return start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")


def local_time_to_utc_iso(date: dt_date, time_str: str) -> str:
    """Convert a date and local time string (HH:MM) in Warsaw timezone to UTC ISO string."""
    hour, minute = map(int, time_str.split(":"))
    local_dt = datetime.combine(date, time(hour, minute), tzinfo=WARSAW_TZ)
    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_day_and_month(date_string: str | None) -> dt_date:
    """
    Parse a date string in formats:
    - DD.MM.YYYY
    - DD.MM
    - DD (day in the current month and year)
    - None (returns today)
    Raises ValueError if parsing fails.
    """
    today = dt_date.today()
    if not date_string:
        return today
    parts = date_string.split(".")
    try:
        if len(parts) == 3:
            # Format: DD.MM.YYYY
            day, month, year = map(int, parts)
            return dt_date(year, month, day)
        elif len(parts) == 2:
            # Format: DD.MM
            day, month = map(int, parts)
            return dt_date(today.year, month, day)
        elif len(parts) == 1:
            value = int(parts[0])
            # Always treat as day of current month/year
            return dt_date(today.year, today.month, value)
    except Exception:
        raise ValueError(f"Invalid date format: '{date_string}'")
    raise ValueError(f"Invalid date format: '{date_string}'")


def sum_entry_durations(entries: list[dict]) -> int:
    """
    Sum the durations of all time entries in seconds.
    Skips entries with missing or invalid timestamps (e.g., running timers).
    """
    total = 0
    for entry in entries:
        time_interval = entry.get("timeInterval") or {}
        start = time_interval.get("start")
        end = time_interval.get("end")
        if not start or not end:
            continue
        try:
            start_dt = utc_iso_to_warsaw_local(start)
            end_dt = utc_iso_to_warsaw_local(end)
            total += int((end_dt - start_dt).total_seconds())
        except (TypeError, ValueError):
            continue
    return total
