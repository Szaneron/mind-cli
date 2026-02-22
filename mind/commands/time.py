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
    validate_issue_key,
    validate_month,
    validate_time_period,
)
from mind.common.utils import get_branch_issue_key
from mind.services.time_commands import (
    TimeHoursService,
    TimeLogService,
    TimeShowService,
)

_TIME_PERIOD_PATTERN = re.compile(r"^\d{1,2}(:\d{2})?-\d{1,2}(:\d{2})?$")


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

    ISSUE_KEY: Jira issue key (e.g., PROJ-123) — auto-detected from Git branch if omitted
    TIME_PERIOD: Time range (e.g., 9-17 or 9:30-12:45)
    DATE: Optional date (e.g., 15.11), defaults to today
    """
    # Shifting logic: if first arg looks like a time period (not an issue key), shift arguments.
    # The `date` callback already ran and set date=today when not provided, so we must not
    # overwrite it with None — only replace it when time_period holds an actual date string.
    if issue_key is not None and _TIME_PERIOD_PATTERN.match(issue_key):
        if time_period is not None and re.match(
            r"^\d{1,2}(\.\d{1,2}(\.\d{4})?)?$", time_period
        ):
            # Second arg looks like a date string — parse it and use as date (raise on invalid)
            date = validate_date(None, None, time_period)
        time_period = issue_key
        issue_key = None
        # date already holds the correct value: either today (from callback) or the parsed date above

    # Auto-detect issue key from Git branch when not provided
    if issue_key is None:
        issue_key = get_branch_issue_key()
        if issue_key is None:
            raise click.UsageError(
                click.style(
                    "❌ No issue key provided and could not detect one from the current Git branch.",
                    fg="red",
                )
            )
        click.echo(
            click.style(
                f"🧠 Logging time using issue key from branch: {issue_key}", fg="cyan"
            )
        )

    # Validate the issue key (raises BadParameter on invalid format)
    issue_key = validate_issue_key(None, None, issue_key)

    # Validate the time period
    if time_period is None:
        raise click.UsageError(
            click.style(
                "❌ TIME_PERIOD is required (e.g., 9-17 or 9:30-12:45).", fg="red"
            )
        )
    time_period = validate_time_period(None, None, time_period)

    TimeLogService().log_time(issue_key, time_period, date, force=force)


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
