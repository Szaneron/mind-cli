import re
from datetime import date as dt_date
from datetime import datetime

import httpx
from rich.console import Console

from mind.common.utils import (
    day_range_utc,
    local_time_to_utc_iso,
    utc_iso_to_warsaw_local,
)
from mind.config.settings import CLOCKIFY_PROJECT_ID, PROJECT_KEY, TASK_PROVIDER
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

    def log_time(
        self, issue_key: str, time_period: str, date: dt_date, force: bool = False
    ) -> None:
        """
        Log time for a given issue and time period on the given date.
        Supports only Jira (TASK_PROVIDER='jira'). Trello is not yet supported.
        Prevents duplicate entries for the same task and exact time range unless --force is used.
        """
        if TASK_PROVIDER != "jira":
            self.console.print(
                "[yellow]⚠️ Only Jira is supported at the moment.[/yellow]"
            )
            return

        try:
            start_time, end_time = self._parse_time_period(time_period)
            description, labels = self._build_description_and_labels(issue_key)
            task = self._find_or_create_task(issue_key)
            tag_ids = self._resolve_tag_ids(labels)
            payload = self._build_payload(
                date, start_time, end_time, description, task["id"], tag_ids
            )

            day_entries = self._fetch_day_entries(date)
            all_ranges = self._get_task_time_ranges(task["id"], description, day_entries)
            has_overlap = self._detect_overlap(
                task["id"], date, start_time, end_time, description, day_entries
            )
            if has_overlap and not force:
                hours_str = ", ".join(all_ranges)
                self.console.print(
                    f"[yellow]⚠️  Overlapping entry detected for [blue]{issue_key}[/blue] on [blue]{date.strftime('%d-%m-%Y')}[/blue] ({start_time}–{end_time}).[/yellow]"
                )
                self.console.print(
                    f"[yellow]🕓 All logged hours for this task: {hours_str}[/yellow]"
                )
                self.console.print(
                    "[yellow]⛔ Use --force to add anyway (total time will be larger).[/yellow]"
                )
                return

            self.clockify.create_time_entry(payload)
            description_colored = re.sub(
                r"\[(PEG-\d+)\]", r"[blue][\1][/blue]", description
            )
            self.console.print(f"✅ Logged: {description_colored}")
            self.console.print(
                f"🕒 {date.strftime('%d-%m-%Y')} | {start_time} – {end_time}"
            )
        except httpx.HTTPStatusError as e:
            project_key = PROJECT_KEY.upper()

            if e.response.status_code == 404:
                self.console.print(
                    f"[red]❌ Task {issue_key} not found in {project_key}.[/red]"
                )
            else:
                self.console.print(f"[red]❌ {project_key} error: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]❌ Error logging time: {e}[/red]")

    def _fetch_day_entries(self, date: dt_date) -> list[dict]:
        """Fetch all Clockify entries for the given day."""
        day_start, day_end = day_range_utc(date)
        return self.clockify.get_time_entries(day_start, day_end)

    def _get_task_time_ranges(
        self,
        task_id: str,
        description: str = None,
        entries: list[dict] = None,
    ) -> list[str]:
        """
        Returns all logged time ranges for the task on the given day.
        """
        all_ranges = []
        for entry in (entries or []):
            interval = entry.get("timeInterval", {})
            start, end = interval.get("start"), interval.get("end")
            if not start or not end:
                continue
            same_task = (str(entry.get("taskId")) == str(task_id)) or (
                description and entry.get("description") == description
            )
            if same_task:
                local_start = utc_iso_to_warsaw_local(start).strftime("%H:%M")
                local_end = utc_iso_to_warsaw_local(end).strftime("%H:%M")
                all_ranges.append(f"{local_start}–{local_end}")
        return sorted(set(all_ranges), key=lambda x: x.split("–")[0])

    def _detect_overlap(
        self,
        task_id: str,
        date: dt_date,
        start_time: str,
        end_time: str,
        description: str = None,
        entries: list[dict] = None,
    ) -> bool:
        """
        Returns True if the new entry overlaps with any existing entry for the task.
        """
        entry_start_dt = datetime.fromisoformat(
            local_time_to_utc_iso(date, start_time).replace("Z", "+00:00")
        )
        entry_end_dt = datetime.fromisoformat(
            local_time_to_utc_iso(date, end_time).replace("Z", "+00:00")
        )
        for entry in (entries or []):
            interval = entry.get("timeInterval", {})
            start, end = interval.get("start"), interval.get("end")
            if not start or not end:
                continue
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            same_task = (str(entry.get("taskId")) == str(task_id)) or (
                description and entry.get("description") == description
            )
            if same_task and start_dt < entry_end_dt and end_dt > entry_start_dt:
                return True
        return False

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

    def _build_description_and_labels(self, issue_key: str) -> tuple[str, list[str]]:
        """Fetch Jira issue data and build the Clockify entry description and label list."""
        issue = self.jira.get_issue(issue_key, ["summary", "labels", "issuetype"])
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")
        labels = fields.get("labels", [])
        issue_type = fields.get("issuetype", {}).get("name")
        description = f"[{issue_key}] {summary}"
        if issue_type:
            labels = [*labels, issue_type]
        return description, labels

    def _resolve_tag_ids(self, tag_names: list[str]) -> list[str]:
        """Resolve Clockify tag names to their IDs."""
        all_tags = self.clockify.get_tags()
        lowercase_names = [name.lower() for name in tag_names]
        return [tag["id"] for tag in all_tags if tag["name"].lower() in lowercase_names]

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
