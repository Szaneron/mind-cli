"""
Commands for managing favorite tasks.

Includes:
- fav add: Mark a task as favorite
- fav remove: Remove a task from favorites
- fav list: List all favorite tasks
"""

import click

from mind.commands.validation import validate_issue_key
from mind.services.favorites_commands import FavoritesService


@click.group(invoke_without_command=True)
@click.pass_context
def fav(ctx: click.Context) -> None:
    """Manage favorite tasks for faster time logging. Defaults to 'list' when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(fav_list)


@fav.command("add")
@click.argument("issue_key", callback=validate_issue_key)
def fav_add(issue_key: str) -> None:
    """
    Mark a task as favorite.

    ISSUE_KEY: Jira issue key (e.g., PROJ-123)
    """
    FavoritesService().add(issue_key)


@fav.command("remove")
@click.argument("issue_key", callback=validate_issue_key)
def fav_remove(issue_key: str) -> None:
    """
    Remove a task from favorites.

    ISSUE_KEY: Jira issue key (e.g., PROJ-123)
    """
    FavoritesService().remove(issue_key)


@fav.command("list")
def fav_list() -> None:
    """List all favorite tasks."""
    FavoritesService().list_all()


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
