"""
Jira API service.

Provides functions for communicating with the Jira API:
- Fetching issue data
- Fetching summary, labels, issue type
"""

import base64

import httpx

from mind.config.settings import JIRA_API_TOKEN, JIRA_BASE_URL, JIRA_EMAIL


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

    def build_description_and_labels(self, issue_key: str) -> tuple[str, list[str]]:
        """
        Build description and labels for a time entry.

        Returns:
            Tuple: (description, labels)
        """
        issue = self.get_issue(issue_key, ["summary", "labels", "issuetype"])
        fields = issue.get("fields", {})

        summary = fields.get("summary", "")
        labels = fields.get("labels", [])
        issue_type = fields.get("issuetype", {}).get("name")

        description = f"[{issue_key}] {summary}"
        if issue_type:
            labels = [*labels, issue_type]

        return description, labels
