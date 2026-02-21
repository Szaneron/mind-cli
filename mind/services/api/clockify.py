"""
Clockify API service.

Provides functions for communicating with the Clockify API:
- Fetching time entries
- Creating time entries
- Managing tasks and tags
"""

import time as time_module

import httpx

from mind.config.settings import (
    CLOCKIFY_API_KEY,
    CLOCKIFY_BASE_API_URL,
    CLOCKIFY_PROJECT_ID,
    CLOCKIFY_REPORTS_API_URL,
    CLOCKIFY_USER_ID,
    CLOCKIFY_WORKSPACE_ID,
)


class ClockifyAPI:
    """Clockify API client."""

    def __init__(self) -> None:
        self.base_url = CLOCKIFY_BASE_API_URL
        self.reports_url = CLOCKIFY_REPORTS_API_URL
        self.api_key = CLOCKIFY_API_KEY
        self.workspace_id = CLOCKIFY_WORKSPACE_ID
        self.project_id = CLOCKIFY_PROJECT_ID
        self.user_id = CLOCKIFY_USER_ID
        self.client = httpx.Client(timeout=10)

    @property
    def headers(self) -> dict[str, str]:
        """Authorization headers for the Clockify API."""
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def get_time_entries(self, start: str, end: str) -> list[dict]:
        """
        Fetch time entries for a user in the given range.

        Args:
            user_id: Clockify user ID
            start: Start date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
            end: End date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
        """
        url = f"{self.base_url}/workspaces/{self.workspace_id}/user/{self.user_id}/time-entries"
        params = {"start": start, "end": end, "page-size": 5000}
        response = self.client.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def create_time_entry(self, payload: dict) -> dict:
        """Create a new time entry."""
        url = f"{self.base_url}/workspaces/{self.workspace_id}/time-entries"
        response = self.client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def find_task_by_name(self, task_name: str) -> dict | None:
        """Find a task by name."""
        url = f"{self.base_url}/workspaces/{self.workspace_id}/projects/{self.project_id}/tasks"
        params = {"name": task_name, "strict-name-search": "true", "page-size": 500}
        response = self.client.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        tasks = response.json()
        return next(
            (
                task
                for task in tasks
                if task["name"].strip().lower() == task_name.strip().lower()
            ),
            None,
        )

    def create_task(self, task_name: str) -> dict:
        """Create a new task in the project."""
        url = f"{self.base_url}/workspaces/{self.workspace_id}/projects/{self.project_id}/tasks"
        payload = {"name": task_name, "projectId": self.project_id}
        response = self.client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def get_tags(self) -> list[dict]:
        """Fetch all tags from the workspace."""
        url = f"{self.base_url}/workspaces/{self.workspace_id}/tags"
        params = {"page-size": 500}
        response = self.client.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_tag_ids_by_names(self, tag_names: list[str]) -> list[str]:
        """Get tag IDs by their names."""
        all_tags = self.get_tags()
        lowercase_names = [name.lower() for name in tag_names]
        return [tag["id"] for tag in all_tags if tag["name"].lower() in lowercase_names]

    def submit_summary_report(
        self, start_date: str, end_date: str, export_pdf: bool = False
    ) -> str:
        """
        Submit an async summary report request to the Clockify Reports API.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
            export_pdf: Whether to request PDF export.

        Returns:
            The reportTaskId for polling.
        """
        base = f"{self.reports_url}/report/workspaces/{self.workspace_id}/async/reports/summary"
        url = f"{base}?export=pdf" if export_pdf else base

        payload = {
            "dateRangeStart": f"{start_date}T00:00:00Z",
            "dateRangeEnd": f"{end_date}T23:59:59.999Z",
            "sortOrder": "ASCENDING",
            "description": "",
            "rounding": False,
            "withoutDescription": False,
            "timeViewMode": "TIME_SENSITIVE_VIEW",
            "amounts": [],
            "amountShown": "HIDE_AMOUNT",
            "zoomLevel": "MONTH",
            "userLocale": "pl-PL",
            "customFields": None,
            "userCustomFields": None,
            "kioskIds": [],
            "users": {
                "contains": "CONTAINS",
                "ids": [self.user_id],
                "status": "ACTIVE_WITH_PENDING",
                "numberOfDeleted": 0,
            },
            "userGroups": {
                "contains": "CONTAINS",
                "ids": [],
                "status": "ACTIVE_WITH_PENDING",
                "numberOfDeleted": 0,
            },
            "summaryFilter": {
                "page": 1,
                "pageSize": 50,
                "sortColumn": "GROUP",
                "groups": ["PROJECT", "TIMEENTRY"],
                "summaryChartType": "BILLABILITY",
            },
        }
        if export_pdf:
            payload["exportType"] = "PDF"

        max_retries = 3
        for attempt in range(max_retries):
            response = self.client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            if not response.text.strip():
                if attempt < max_retries - 1:
                    time_module.sleep(2)
                    continue
                raise RuntimeError(
                    "Clockify report API returned empty response after several attempts."
                )
            data = response.json()
            task_id = data.get("reportTaskId")
            if not task_id:
                raise RuntimeError("Failed to submit report task (no reportTaskId).")
            return task_id

    def fetch_report_json(
        self, task_id: str, max_retries: int = 3, poll_interval: int = 2
    ) -> dict:
        """
        Poll for async summary report JSON results.

        Returns:
            The report data dict containing totals.
        """
        url = f"{self.reports_url}/report/workspaces/{self.workspace_id}/async/reports/summary/{task_id}"

        for _ in range(max_retries):
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()
            if not response.text.strip():
                time_module.sleep(poll_interval)
                continue
            data = response.json()
            if data.get("totals"):
                return data
            time_module.sleep(poll_interval)

        raise RuntimeError(
            f"Failed to fetch report results after {max_retries} attempts."
        )

    def download_report_pdf(
        self,
        task_id: str,
        filepath: str,
        max_retries: int = 3,
        poll_interval: int = 4,
    ) -> None:
        """
        Poll for async PDF report and save to file.

        Args:
            task_id: The reportTaskId from submit_summary_report.
            filepath: Destination file path.
            max_retries: Maximum poll attempts.
            poll_interval: Seconds between polls.
        """
        url = f"{self.reports_url}/report/workspaces/{self.workspace_id}/async/reports/summary/{task_id}"

        for _ in range(max_retries):
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()

            if response.content[:5] == b"%PDF-":
                with open(filepath, "wb") as f:
                    f.write(response.content)
                return

            time_module.sleep(poll_interval)

        raise RuntimeError(
            f"Failed to download PDF report after {max_retries} attempts."
        )
