"""
Commands for managing favorite tasks.

Includes:
- fav add: Mark a task as favorite (optionally with a default time via --time)
- fav remove: Remove a task from favorites
- fav list: List all favorite tasks
"""

import click

from mind.commands.validation import validate_time_period
from mind.services.favorites_commands import FavoritesService


@click.group(invoke_without_command=True)
@click.pass_context
def fav(ctx: click.Context) -> None:
    """Manage favorite tasks for faster time logging. Defaults to 'list' when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(fav_list)


@fav.command("add")
@click.argument("identifier")
@click.argument("text", required=False)
@click.option(
    "--time",
    "-t",
    "default_time",
    callback=validate_time_period,
    help="Default time period (e.g. 9-17) used by 'mind log' when none is given.",
)
def fav_add(identifier: str, text: str | None, default_time: str | None) -> None:
    """
    Mark a task as favorite, or update an existing one's text/default time.

    IDENTIFIER: Jira issue key (e.g., PROJ-123) or a short alias.
    TEXT: Optional plain text — when given, stores a text favorite without any API call.

    \b
    Examples:
      mind fav add PROJ-123                        Jira favorite (fetches the summary)
      mind fav add ds "Daily Standup"               Text favorite, no API call
      mind fav add ds "Daily Standup" --time 9-15   Text favorite with a default time
      mind fav add ds --time 9-15                   Set/update default time on an existing favorite
      mind fav add PROJ-123 --time 9-17             Set/update default time on an existing Jira favorite

    Once a favorite has a default time, 'mind log <alias> <date>' logs it without
    needing a TIME_PERIOD (e.g. 'mind log ds 08').
    """
    FavoritesService().add(identifier, text, default_time)


@fav.command("remove")
@click.argument("identifier")
def fav_remove(identifier: str) -> None:
    """
    Remove a task from favorites.

    IDENTIFIER: Jira issue key (e.g., PROJ-123) or alias.
    """
    FavoritesService().remove(identifier)


@fav.command("list")
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    default=False,
    help="Show favorites from all providers, not just the active one.",
)
def fav_list(show_all: bool) -> None:
    """List favorite tasks for the active provider (use --all for every provider)."""
    FavoritesService().list_all(show_all=show_all)


@fav.command("clear")
def fav_clear() -> None:
    """Clear all favorite tasks after confirmation."""
    service = FavoritesService()
    if service.is_empty():
        click.secho("Favorites list is already empty.", fg="yellow")
        return
    if not click.confirm(
        "💭 Are you sure you want to clear all favorites? This cannot be undone."
    ):
        click.secho("❌ Cancelled. Favorites list not cleared.", fg="yellow")
        return
    if service.clear():
        click.secho("🧹 All favorites have been cleared.", fg="green")
