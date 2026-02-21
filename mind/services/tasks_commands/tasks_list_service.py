"""
Service for listing Jira tasks assigned to the current user.
"""

from rich.console import Console

from mind.services.api import JiraAPI


class TasksListService:
    """
    Service for fetching and displaying Jira issues assigned to the current user.
    """

    def __init__(self) -> None:
        """Initialize the service with console and Jira API client."""
        self.console = Console()
        self.jira = JiraAPI()

    def list_tasks(self, active_only: bool = False, project: str | None = None) -> None:
        """
        Fetch and display Jira issues assigned to the current user.

        Args:
            active_only: If True, shows only tasks with status "In Progress" or "Code Review".
            project: Optional project key to filter (e.g. 'PEG').
        """
        try:
            issues = self.jira.get_assigned_issues(
                active_only=active_only, project=project
            )
            self._print_issues(issues, active_only, project)
        except Exception as e:
            self.console.print(f"[red]❌ Error fetching tasks: {e}[/red]")

    def _print_issues(
        self, issues: list[dict], active_only: bool, project: str | None
    ) -> None:
        """Print the list of issues to the console, sorted by custom status order."""
        filter_label = "active (In Progress, Code Review)" if active_only else "open"
        project_label = f" for project [blue]{project}[/blue]" if project else ""

        if not issues:
            self.console.print(
                f"[yellow]No {filter_label} tasks assigned to you{project_label}.[/yellow]"
            )
            return

        issues_sorted = sorted(issues, key=self._status_key)

        self.console.print(
            f"📋 [bold]Your {filter_label} Jira tasks{project_label} ([blue]{len(issues_sorted)}[/blue]):[/bold]"
        )
        for issue in issues_sorted:
            key = issue["key"]
            summary = issue["summary"]
            status = issue["status"]
            self.console.print(
                f"  [blue]{key}[/blue] | [cyan]{status}[/cyan] | {summary}"
            )

    def _status_key(self, issue: dict) -> int:
        """Return sort key for issue status."""
        status_order = [
            "IN PROGRESS",
            "ANALYSIS",
            "CODE REVIEW",
            "TO DO",
            "ON STAGING",
            "READY FOR PRODUCTION",
            "READY FOR QA",
            "QA FAILED",
            "ON HOLD",
        ]
        status = issue["status"].strip().upper()
        for idx, s in enumerate(status_order):
            if status == s:
                return idx

        return len(status_order)
