"""
Commands related to time logging (Clockify/Jira).

Includes:
- log: Log time to Clockify
- show: Display logged entries
- hours: Monthly hours summary
"""

import re
from datetime import date as dt_date

import click

from mind.commands.validation import (
    validate_date,
    validate_month,
    validate_time_period,
)
from mind.services.favorites_commands import FavoritesService
from mind.services.time_commands import (
    TimeHoursService,
    TimeLogService,
    TimeShowService,
)

_TIME_PERIOD_PATTERN = re.compile(r"^\d{1,2}(:\d{2})?-\d{1,2}(:\d{2})?$")
_DATE_ARG_PATTERN = re.compile(r"^\d{1,2}(\.\d{1,2}(\.\d{4})?)?$")


@click.command()
@click.argument("issue_key", required=False, default=None)
@click.argument("time_period", required=False, default=None)
@click.argument("date", required=False, callback=validate_date)
@click.option("--force", is_flag=True, help="Override duplicate entry protection.")
def log(
    issue_key: str | None,
    time_period: str | None,
    date: dt_date | None,
    force: bool = False,
) -> None:
    """
    Log time to Clockify.

    \b
    ISSUE_KEY: Jira issue key (e.g., PROJ-123) — auto-detected from Git branch if omitted
    TIME_PERIOD: Time range (e.g., 9-17 or 9:30-12:45) — optional if the favorite has a
                 default time set (see 'mind fav add --help')
    DATE: Optional date (e.g., 15.11), defaults to today

    \b
    Examples:
      mind log PROJ-123 9-17         Explicit issue + time period, today
      mind log ds 9-17 08            Explicit issue + time period + date
      mind log ds 08                 Favorite's default time, date = 8th of this month
      mind log ds                    Favorite's default time, today
    """
    # Shifting logic: if first arg looks like a time period (not an issue key), shift arguments.
    # The `date` callback already ran and set date=today when not provided, so we must not
    # overwrite it with None — only replace it when time_period holds an actual date string.
    if issue_key is not None and _TIME_PERIOD_PATTERN.match(issue_key):
        if time_period is not None and _DATE_ARG_PATTERN.match(time_period):
            # Second arg looks like a date string — parse it and use as date (raise on invalid)
            date = validate_date(None, None, time_period)
        time_period = issue_key
        issue_key = None
        # date already holds the correct value: either today (from callback) or the parsed date above
    elif (
        time_period is not None
        and _DATE_ARG_PATTERN.match(time_period)
        and not _TIME_PERIOD_PATTERN.match(time_period)
    ):
        # Second arg is a date, not a time period (e.g. 'mind log ds 08') — the time period
        # will come from the favorite's default time instead.
        date = validate_date(None, None, time_period)
        time_period = None

    # The task identifier (issue_key) may be None — the provider/resolver handles favorites,
    # explicit text and provider fallback (e.g. Jira branch key, Trello branch name).

    if time_period is None:
        time_period = _resolve_default_time(issue_key)
    time_period = validate_time_period(None, None, time_period)

    TimeLogService().log_time(issue_key, time_period, date, force=force)


def _resolve_default_time(issue_key: str | None) -> str:
    """Fall back to the favorite's stored default time when TIME_PERIOD is omitted."""
    favorite = FavoritesService().find(issue_key) if issue_key else None
    if favorite is not None:
        default_time = favorite.get("default_time")
        if default_time:
            return default_time
        raise click.UsageError(
            click.style(
                f"❌ Favorite '{issue_key}' has no default time set. "
                f"Provide TIME_PERIOD explicitly, or set one with: "
                f"mind fav add {issue_key} --time 9-17",
                fg="red",
            )
        )
    raise click.UsageError(
        click.style("❌ TIME_PERIOD is required (e.g., 9-17 or 9:30-12:45).", fg="red")
    )


@click.command()
@click.argument("date", required=False, callback=validate_date)
def show(date: dt_date | None) -> None:
    """
    Display logged entries from Clockify.

    DATE: Optional date (e.g., 15.11), defaults to today
    """
    TimeShowService().show_entries(date)


@click.command()
@click.argument("month", required=False, type=int, callback=validate_month)
def hours(month: int | None) -> None:
    """
    Show total hours for a month.

    MONTH: Month number (1-12), defaults to current
    """
    TimeHoursService().show_hours(month)
