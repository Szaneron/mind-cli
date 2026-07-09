"""
Task resolution with priority ordering.

Resolves raw user input into a TaskEntry using a strict priority:
1. Favorites  (highest) — input matches a stored favorite key/alias.
2. Explicit text         — input contains spaces (e.g. "Quick prod fix").
3. Provider fallback     — Jira queries its API; Trello parses the Git branch.
"""

from mind.services.providers.base import TaskEntry, TaskProvider
from mind.services.providers.factory import get_task_provider


class TaskResolver:
    """Resolves user input into a TaskEntry, independent of the active provider."""

    def __init__(self, provider: TaskProvider | None = None, favorites=None) -> None:
        # Local import to avoid a circular import (favorites -> providers -> favorites).
        from mind.services.favorites_commands import FavoritesService

        self.provider = provider or get_task_provider()
        self.favorites = favorites or FavoritesService()

    def resolve(self, raw_input: str | None) -> TaskEntry:
        """Resolve raw input into a TaskEntry following the priority order."""
        if raw_input:
            favorite = self.favorites.find(raw_input)
            if favorite is not None:
                from mind.services.favorites_commands import FavoritesService

                return FavoritesService.favorite_to_task_entry(favorite)

            if " " in raw_input.strip():
                return TaskEntry(task_name=raw_input, description=raw_input, labels=[], use_clockify_task=False)

        return self.provider.resolve_entry(raw_input)
