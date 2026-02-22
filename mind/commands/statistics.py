"""
Command for the monthly statistics dashboard.

Includes:
- stats: Display a monthly stats dashboard (time summary, office/remote ratio,
         stability, and highlights)
"""

import click

from mind.commands.validation import validate_month
from mind.services.statistics_commands import StatisticsDashboardService


@click.command()
@click.argument("month", required=False, type=int, callback=validate_month)
@click.option("--compact", is_flag=True, help="Print a compact single-line summary.")
def stats(month: int | None, compact: bool) -> None:
    """
    Display monthly statistics dashboard.

    MONTH: Month number (1-12), defaults to current month.

    Shows logged vs planned time, office/remote ratio, day-level stability,
    highlights (most overtime / most missing), and average hours per day.
    Use --compact for a concise single-line output.
    """
    StatisticsDashboardService().show_stats(month=month, compact=compact)
