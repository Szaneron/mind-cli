"""
Commands related to time logging (Clockify/Jira).

Includes:
- log: Log time to Clockify
- show: Display logged entries
- hours: Monthly hours summary
"""

from datetime import date as dt_date

import click

from mind.commands.validation import (
    validate_date,
    validate_issue_key,
    validate_month,
    validate_time_period,
)
from mind.services.time_commands import (
    TimeHoursService,
    TimeLogService,
    TimeShowService,
)


@click.command()
@click.argument("issue_key", callback=validate_issue_key)
@click.argument("time_period", callback=validate_time_period)
@click.argument("date", required=False, callback=validate_date)
def log(issue_key: str, time_period: str, date: dt_date | None) -> None:
    """
    Log time to Clockify.

    ISSUE_KEY: Jira issue key (e.g., PROJ-123)
    TIME_PERIOD: Time range (e.g., 9-17 or 9:30-12:45)
    DATE: Optional date (e.g., 15.11), defaults to today
    """
    TimeLogService().log_time(issue_key, time_period, date)


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
