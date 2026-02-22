"""
Commands for monthly statistics (dashboard, heatmap).

Includes:
- stats dash:    Display a monthly stats dashboard
- stats heatmap: Display a daily hours heatmap for a given month
"""

import click

from mind.commands.validation import validate_month
from mind.services.statistics_commands import (
    StatisticsDashboardService,
    StatisticsHeatmapService,
)


@click.group(invoke_without_command=True)
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Monthly statistics commands. Defaults to 'dash' when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(dash)


@stats.command("dash")
@click.argument("month", required=False, type=int, callback=validate_month)
@click.option("--compact", is_flag=True, help="Print a compact single-line summary.")
def dash(month: int | None, compact: bool) -> None:
    """
    Display monthly statistics dashboard.

    MONTH: Month number (1-12), defaults to current month.

    \b
    Examples:
      mind stats dash
      mind stats dash 11
      mind stats dash --compact
      mind stats dash 11 --compact
    """
    StatisticsDashboardService().show_stats(month=month, compact=compact)


@stats.command("heatmap")
@click.argument("month", required=False, type=int, callback=validate_month)
def heatmap(month: int | None) -> None:
    """
    Display a daily hours heatmap for a given month.

    MONTH: Month number (1-12), defaults to current month.

    \b
    Examples:
      mind stats heatmap
      mind stats heatmap 11
    """
    StatisticsHeatmapService().show_heatmap(month=month)
