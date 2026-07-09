"""
Trello task provider.

Does NOT integrate with the Trello API. Task descriptions come from the current
Git branch name (or explicit text), and recurring items are handled via text favorites.
"""

from mind.common.utils import get_current_branch, humanize_branch_name
from mind.services.providers.base import (
    ListingNotSupportedError,
    TaskEntry,
    TaskProvider,
)


class TrelloTaskProvider(TaskProvider):
    """Task provider that derives tasks from the Git branch instead of an API."""

    name = "trello"

    def resolve_entry(self, identifier: str | None) -> TaskEntry:
        """Use the given text, or humanize the current Git branch name."""
        text = identifier or humanize_branch_name(get_current_branch())
        if not text:
            raise ValueError(
                "No task text provided and could not derive one from the current Git branch."
            )
        return TaskEntry(task_name=text, description=text, labels=[], use_clockify_task=False)

    def get_summary(self, identifier: str) -> str:
        """Return a human-readable summary for an identifier."""
        return humanize_branch_name(identifier) or identifier

    def list_tasks(self, active_only: bool, project: str | None) -> list[dict]:
        """Trello has no API integration — listing is unsupported."""
        raise ListingNotSupportedError(self.name)
