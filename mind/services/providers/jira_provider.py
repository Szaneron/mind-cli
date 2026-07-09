"""
Jira task provider.

Wraps the JiraAPI client and exposes it through the TaskProvider interface.
The description/label building logic mirrors the previous TimeLogService behaviour 1:1.
"""

from mind.common.utils import get_branch_issue_key
from mind.services.api import JiraAPI
from mind.services.providers.base import TaskEntry, TaskProvider


class JiraTaskProvider(TaskProvider):
    """Task provider backed by the live Jira API."""

    name = "jira"

    def __init__(self) -> None:
        self.jira = JiraAPI()

    def resolve_entry(self, identifier: str | None) -> TaskEntry:
        """Resolve a Jira issue key into a TaskEntry. Falls back to the Git branch key."""
        issue_key = identifier or get_branch_issue_key()
        if not issue_key:
            raise ValueError(
                "No issue key provided and could not detect one from the current Git branch."
            )
        issue_key = issue_key.upper()

        issue = self.jira.get_issue(issue_key, ["summary", "labels", "issuetype"])
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")
        labels = fields.get("labels", [])
        issue_type = fields.get("issuetype", {}).get("name")
        if issue_type:
            labels = [*labels, issue_type]

        return TaskEntry(
            task_name=issue_key,
            description=f"[{issue_key}] {summary}",
            labels=labels,
        )

    def get_summary(self, identifier: str) -> str:
        """Fetch the issue summary for a Jira key (used by 'fav add')."""
        return self.jira.get_issue_summary(identifier)

    def list_tasks(self, active_only: bool, project: str | None) -> list[dict]:
        """List Jira issues assigned to the current user."""
        return self.jira.get_assigned_issues(active_only=active_only, project=project)
