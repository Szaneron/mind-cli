"""
Jira API service.

Provides functions for communicating with the Jira API:
- Fetching issue data
- Fetching summary, labels, issue type
"""

import base64

import httpx

from mind.config.settings import JIRA_API_TOKEN, JIRA_BASE_URL, JIRA_EMAIL, PROJECT_KEY


class JiraAPI:
    """Jira API client."""

    def __init__(self) -> None:
        self.base_url = JIRA_BASE_URL
        self.email = JIRA_EMAIL
        self.api_token = JIRA_API_TOKEN
        self.client = httpx.Client(timeout=10)

    @property
    def headers(self) -> dict[str, str]:
        """Authorization headers for Jira API (Basic Auth)."""
        credentials = f"{self.email}:{self.api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get_issue(self, issue_key: str, fields: list[str] | None = None) -> dict:
        """
        Fetch issue data from Jira.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            fields: List of fields to fetch (default: summary, labels, issuetype)
        """
        fields = fields or ["summary", "labels", "issuetype"]
        fields_param = ",".join(fields)
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        params = {"fields": fields_param}

        response = self.client.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_issue_summary(self, issue_key: str) -> str:
        """Fetch issue summary."""
        issue = self.get_issue(issue_key, ["summary"])
        return issue.get("fields", {}).get("summary", "")

    def get_issue_labels(self, issue_key: str) -> list[str]:
        """Fetch issue labels."""
        issue = self.get_issue(issue_key, ["labels"])
        return issue.get("fields", {}).get("labels", [])

    def get_issue_type(self, issue_key: str) -> str:
        """Fetch issue type."""
        issue = self.get_issue(issue_key, ["issuetype"])
        return issue.get("fields", {}).get("issuetype", {}).get("name", "")

    def get_assigned_issues(
        self, active_only: bool = False, project: str | None = None
    ) -> list[dict]:
        """
        Fetch open Jira issues assigned to the current user.

        Args:
            active_only: If True, returns only issues with status "In Progress" or "Code Review".
            project: Optional project key to filter (default: PROJECT_KEY).

        Returns:
            List of issue dicts with keys: key, summary, status.
        """
        if project is None:
            project = PROJECT_KEY
        if project:
            if active_only:
                jql = (
                    f"project = {project} AND assignee = currentUser() AND "
                    f'(status = "In Progress" OR status = "Code Review") ORDER BY updated DESC'
                )
            else:
                jql = f"project = {project} AND assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC"
        else:
            if active_only:
                jql = 'assignee = currentUser() AND (status = "In Progress" OR status = "Code Review") ORDER BY updated DESC'
            else:
                jql = "assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC"

        url = f"{self.base_url}/rest/api/3/search/jql"
        params = {
            "jql": jql,
            "fields": "summary,status",
            "maxResults": 50,
        }

        response = self.client.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()

        issues = []
        for item in data.get("issues", []):
            fields = item.get("fields", {})
            issues.append(
                {
                    "key": item["key"],
                    "summary": fields.get("summary", ""),
                    "status": fields.get("status", {}).get("name", ""),
                }
            )
        return issues
