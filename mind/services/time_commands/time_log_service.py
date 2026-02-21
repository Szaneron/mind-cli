import re
from datetime import date as dt_date

import httpx
from rich.console import Console

from mind.common.utils import local_time_to_utc_iso
from mind.config.settings import CLOCKIFY_PROJECT_ID, TASK_PROVIDER
from mind.services.api import ClockifyAPI, JiraAPI


class TimeLogService:
    """
    Service for logging time entries to Clockify.
    Fetches task/label data from Jira and creates a time entry in Clockify.
    """

    def __init__(self) -> None:
        """Initialize the service with console, Clockify and Jira API clients."""
        self.console = Console()
        self.clockify = ClockifyAPI()
        self.jira = JiraAPI()

    def log_time(self, issue_key: str, time_period: str, date: dt_date) -> None:
        """
        Log time for a given issue and time period on the given date.
        Supports only Jira (TASK_PROVIDER='jira'). Trello is not yet supported.
        """
        if TASK_PROVIDER != "jira":
            self.console.print(
                "[yellow]⚠️ Only Jira is supported at the moment.[/yellow]"
            )
            return

        try:
            start_time, end_time = self._parse_time_period(time_period)
            description, labels = self.jira.build_description_and_labels(issue_key)
            task = self._find_or_create_task(issue_key)
            tag_ids = self.clockify.get_tag_ids_by_names(labels)
            payload = self._build_payload(
                date, start_time, end_time, description, task["id"], tag_ids
            )
            self.clockify.create_time_entry(payload)
            description_colored = re.sub(
                r"\[(PEG-\d+)\]", r"[blue][\1][/blue]", description
            )
            self.console.print(f"✅ Logged: {description_colored}")
            self.console.print(
                f"🕒 {date.strftime('%d-%m-%Y')} | {start_time} – {end_time}"
            )
        except Exception as e:
            if (
                isinstance(e, httpx.HTTPStatusError)
                and getattr(e.response, "status_code", None) == 404
            ):
                self.console.print(f"[red]❌ Task {issue_key} not found in Jira.[/red]")
            elif isinstance(e, httpx.HTTPStatusError):
                self.console.print(f"[red]❌ Jira error: {e}[/red]")
            else:
                self.console.print(f"[red]❌ Error logging time: {e}[/red]")

    def _parse_time_period(self, time_period: str) -> tuple[str, str]:
        """Parse time period string (e.g. '9-17' or '9:30-12:45') into (HH:MM, HH:MM)."""
        parts = time_period.split("-")
        if len(parts) != 2:
            raise ValueError(f"Invalid time period format: '{time_period}'")
        start_time = self._normalize_time(parts[0])
        end_time = self._normalize_time(parts[1])
        if start_time >= end_time:
            raise ValueError(
                f"End time ({end_time}) must be after start time ({start_time})"
            )
        return start_time, end_time

    def _normalize_time(self, time_str: str) -> str:
        """Normalize a time string like '9' or '9:30' to 'HH:MM'."""
        parts = time_str.strip().split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return f"{hour:02d}:{minute:02d}"

    def _find_or_create_task(self, task_name: str) -> dict:
        """Find an existing Clockify task by name or create a new one."""
        task = self.clockify.find_task_by_name(task_name)
        return task if task else self.clockify.create_task(task_name)

    def _build_payload(
        self,
        date: dt_date,
        start_time: str,
        end_time: str,
        description: str,
        task_id: str,
        tag_ids: list[str],
    ) -> dict:
        """Build the Clockify time entry payload."""
        return {
            "start": local_time_to_utc_iso(date, start_time),
            "end": local_time_to_utc_iso(date, end_time),
            "billable": True,
            "description": description,
            "projectId": CLOCKIFY_PROJECT_ID,
            "taskId": task_id,
            "tagIds": tag_ids,
        }
