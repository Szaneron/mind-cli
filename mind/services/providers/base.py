"""
Task provider abstraction.

Defines the common contract every task source (Jira, Trello, ...) must implement,
plus the TaskEntry value object that consumers (time logging, favorites) use.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TaskEntry:
    """
    A resolved task, ready to be logged to Clockify.

    Attributes:
        task_name: Name used for the Clockify task (Jira: issue key; text/branch: the text itself).
        description: Full description shown on the time entry (Jira: '[KEY] summary').
        labels: Label/tag names to attach (Jira: labels + issue type; text/branch: empty).
        use_clockify_task: Whether to create/find a Clockify task and assign taskId.
                           True for Jira (issue key = task). False for text/branch entries
                           (logs to project only, taskId=null — matches manual web behaviour).
    """

    task_name: str
    description: str
    labels: list[str] = field(default_factory=list)
    use_clockify_task: bool = True


class ListingNotSupportedError(Exception):
    """Raised when a provider cannot list assigned tasks (e.g. Trello has no API integration)."""

    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name
        super().__init__(f"Task listing is not supported for provider '{provider_name}'.")


class TaskProvider(ABC):
    """Abstract task source. Concrete providers wrap a backend (Jira API, Git branch, ...)."""

    name: str = ""

    @abstractmethod
    def resolve_entry(self, identifier: str | None) -> TaskEntry:
        """
        Build a TaskEntry from an identifier.

        identifier=None means the provider should derive the task from context
        (e.g. the current Git branch). Raises ValueError if nothing can be resolved.
        """

    @abstractmethod
    def get_summary(self, identifier: str) -> str:
        """Return a human-readable summary for the identifier (used by 'fav add')."""

    @abstractmethod
    def list_tasks(self, active_only: bool, project: str | None) -> list[dict]:
        """
        Return tasks assigned to the current user.

        Raises ListingNotSupportedError if the provider has no listing capability.
        """
