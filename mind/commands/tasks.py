"""
Commands for listing Jira tasks assigned to the current user.

Includes:
- tasks: Display open Jira issues assigned to the authenticated user
"""

import click

from mind.config.settings import PROJECT_KEY
from mind.services.tasks_commands import TasksListService


@click.command()
@click.option(
    "--active",
    is_flag=True,
    default=False,
    help="Show only in-progress tasks.",
)
@click.option(
    "--project",
    default=PROJECT_KEY,
    show_default=True,
    help="Filter tasks by project key (default from env)",
)
def tasks(active: bool, project: str) -> None:
    """
    Display Jira tasks assigned to you.

    Lists open issues assigned to the current user. Default project is set from the environment variable PROJECT_KEY.
    Use --active to show only in-progress tasks.
    Use --project to filter by project key.
    """
    TasksListService().list_tasks(active_only=active, project=project)
