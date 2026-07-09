"""
Task provider factory.

Selects the active provider based on the TASK_PROVIDER setting.
"""

from mind.config.settings import TASK_PROVIDER
from mind.services.providers.base import TaskProvider
from mind.services.providers.jira_provider import JiraTaskProvider
from mind.services.providers.trello_provider import TrelloTaskProvider

_PROVIDERS: dict[str, type[TaskProvider]] = {
    "jira": JiraTaskProvider,
    "trello": TrelloTaskProvider,
}


def get_task_provider(name: str | None = None) -> TaskProvider:
    """
    Return an instance of the configured task provider.

    Args:
        name: Optional provider name override. Defaults to the TASK_PROVIDER env value.

    Raises:
        ValueError: If the provider name is unknown.
    """
    key = (name or TASK_PROVIDER or "jira").lower()
    provider_cls = _PROVIDERS.get(key)
    if provider_cls is None:
        available = ", ".join(sorted(_PROVIDERS))
        raise ValueError(
            f"Unknown TASK_PROVIDER '{key}'. Available providers: {available}."
        )
    return provider_cls()
