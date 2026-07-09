# Common utilities: date parsing and timezone helpers
import re
import subprocess
from datetime import date as dt_date
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import holidays

from mind.config.settings import WORKING_HOURS_PER_DAY

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


def max_working_hours_in_month(
    year: int,
    month: int,
    country: str = "PL",
) -> int:
    """
    Calculate the maximum possible working hours in a month,
    excluding weekends and public holidays.
    """
    pl_holidays = holidays.country_holidays(country, years=[year])
    first = dt_date(year, month, 1)
    last = (
        dt_date(year, month + 1, 1) - timedelta(days=1)
        if month < 12
        else dt_date(year + 1, 1, 1) - timedelta(days=1)
    )
    working_days = sum(
        1
        for d in range((last - first).days + 1)
        if (first + timedelta(days=d)) not in pl_holidays
        and (first + timedelta(days=d)).weekday() < 5
    )
    return working_days * WORKING_HOURS_PER_DAY


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


def format_duration(seconds: int) -> str:
    """Format a duration in seconds as 'Xh Ym' or 'Xh'."""
    h, rem = divmod(abs(seconds), 3600)
    m = rem // 60
    return f"{h}h {m}m" if m else f"{h}h"


def month_range(month: int | None = None) -> tuple[dt_date, dt_date]:
    """
    Return the first and last date of the given month (defaults to current month).
    """
    today = dt_date.today()
    m = month or today.month
    y = today.year
    first = dt_date(y, m, 1)
    last = (
        dt_date(y, m + 1, 1) if m < 12 else dt_date(y + 1, 1, 1)
    ) - timedelta(days=1)
    return first, last


def get_current_branch() -> str | None:
    """
    Return the current Git branch name (e.g. 'feature/PROJ-123-login'), or None if unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        branch = result.stdout.strip()
        return branch or None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def get_branch_issue_key() -> str | None:
    """
    Detect a Jira issue key from the current Git branch name.
    Returns the issue key (e.g., 'PROJ-123') or None if not found.
    """
    branch = get_current_branch()
    if not branch:
        return None
    match = re.search(r"([A-Z][A-Z0-9]*-\d+)", branch, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def humanize_branch_name(branch: str | None) -> str:
    """
    Turn a Git branch name into a human-readable task description.

    Strips technical prefixes (everything up to and including the last '/'),
    replaces dashes/underscores with spaces, collapses whitespace and
    capitalizes the first letter. E.g. 'feature/login-refactor' -> 'Login refactor'.
    """
    if not branch:
        return ""
    name = branch.rsplit("/", 1)[-1]
    name = re.sub(r"[-_]+", " ", name).strip()
    name = re.sub(r"\s+", " ", name)
    if not name:
        return ""
    return name[0].upper() + name[1:]
