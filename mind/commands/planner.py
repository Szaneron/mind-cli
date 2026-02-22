"""
Commands related to planned availability (Planner).

Includes:
- plan show:    Display planned availability with time ranges and work mode
- plan compare: Compare planned vs logged hours per day
"""

import click

from mind.commands.validation import validate_month
from mind.services.planner_commands import PlanCompareService, PlanShowService


@click.group()
def plan() -> None:
    """
    Manage and view planned availability from the Planner.
    """


@plan.command("show")
@click.argument("month", required=False, type=int, callback=validate_month)
def show(month: int | None) -> None:
    """
    Display planned availability with time ranges and work mode.

    MONTH: Optional month number (1–12), defaults to current month.

    \b
    Examples:
      mind plan show
      mind plan show 11
    """
    PlanShowService().show(month)


@plan.command("compare")
@click.argument("month", required=False, type=int, callback=validate_month)
def compare(month: int | None) -> None:
    """
    Compare planned availability vs logged Clockify hours per day.

    MONTH: Optional month number (1–12), defaults to current month.

    \b
    Examples:
      mind plan compare
      mind plan compare 11
    """
    PlanCompareService().compare(month)
