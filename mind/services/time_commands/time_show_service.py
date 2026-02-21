import re
from datetime import date as dt_date

from rich.console import Console

from mind.common.utils import (
    day_range_utc,
    sum_entry_durations,
    utc_iso_to_warsaw_local,
)
from mind.services.api import ClockifyAPI


class TimeShowService:
    """
    Service for displaying (showing) time entries from Clockify for a given day.
    Handles fetching, formatting, and printing entries for the CLI.
    """

    def __init__(self) -> None:
        """Initialize the service with console and Clockify API client."""
        self.console = Console()
        self.clockify = ClockifyAPI()

    def show_entries(self, date: dt_date) -> None:
        """
        Show logged time entries for a given date (default: today).
        Handles fetching and printing entries. Expects a dt_date object.
        """
        try:
            entries = self._fetch_entries(date)
            self._print_entries(entries, date)
        except Exception as e:
            self.console.print(f"[red]❌ Error fetching entries: {e}[/red]")

    def _fetch_entries(self, date: dt_date) -> list[dict]:
        """
        Fetch time entries from Clockify for the given date.
        """
        user_id = self.clockify.get_user_id()
        start, end = day_range_utc(date)
        return self.clockify.get_time_entries(user_id, start, end)

    def _print_entries(self, entries: list[dict], date: dt_date) -> None:
        """
        Print formatted time entries for the given date.
        """
        date_str = date.strftime("%d.%m.%Y")
        if not entries:
            self.console.print(
                f"🕒 [yellow]No time entries logged for[/yellow] {date_str}"
            )
            return

        total_seconds = sum_entry_durations(entries)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        summary = f" [blue](logged {hours}h {minutes}m)[/blue]" if total_seconds else ""
        self.console.print(f"🕒 [bold]Time entries on {date_str}{summary}:[/bold]")

        for entry in entries:
            try:
                self.console.print(self._format_entry(entry))
            except Exception as e:
                self.console.print(f"[red]❌ Error formatting entry: {e}[/red]")

    def _format_entry(self, entry: dict) -> str:
        """
        Format a single time entry for display.
        """
        try:
            start_str = utc_iso_to_warsaw_local(
                entry["timeInterval"]["start"]
            ).strftime("%H:%M")
            end_val = entry["timeInterval"].get("end")
            if end_val:
                end_str = utc_iso_to_warsaw_local(end_val).strftime("%H:%M")
            else:
                end_str = "--:--"
            description = entry.get("description", "").replace("\n", " ")
            description = re.sub(r"(\[PEG-[^\]]+\])", r"[blue]\1[/blue]", description)
            return (
                f"{start_str}-{end_str} | {description}"
                if end_str != "--:--"
                else f"{start_str} --:-- | {description}"
            )
        except Exception as e:
            raise ValueError(f"Error parsing entry: {e} ({entry})")
