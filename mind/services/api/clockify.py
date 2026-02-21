"""
Clockify API service.

Provides functions for communicating with the Clockify API:
- Fetching time entries
- Creating time entries
- Managing tasks and tags
"""

import httpx

from mind.config.settings import (
    CLOCKIFY_API_KEY,
    CLOCKIFY_BASE_API_URL,
    CLOCKIFY_PROJECT_ID,
    CLOCKIFY_WORKSPACE_ID,
)


class ClockifyAPI:
    """Clockify API client."""

    def __init__(self) -> None:
        self.base_url = CLOCKIFY_BASE_API_URL
        self.api_key = CLOCKIFY_API_KEY
        self.workspace_id = CLOCKIFY_WORKSPACE_ID
        self.project_id = CLOCKIFY_PROJECT_ID
        self.client = httpx.Client(timeout=10)

    @property
    def headers(self) -> dict[str, str]:
        """Authorization headers for the Clockify API."""
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def get_user_id(self) -> str:
        """Get the current user ID."""
        user = self.get_current_user()
        return user["id"]

    def get_current_user(self) -> dict:
        """Fetch current user data."""
        url = f"{self.base_url}/user"
        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_time_entries(self, user_id: str, start: str, end: str) -> list[dict]:
        """
        Fetch time entries for a user in the given range.

        Args:
            user_id: Clockify user ID
            start: Start date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
            end: End date in ISO format (YYYY-MM-DDTHH:MM:SSZ)
        """
        url = f"{self.base_url}/workspaces/{self.workspace_id}/user/{user_id}/time-entries"
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
