from datetime import date as dt_date
from datetime import timedelta

from rich.console import Console

from mind.common.utils import (
    day_range_utc,
    max_working_hours_in_month,
    sum_entry_durations,
)
from mind.config.settings import WORKING_HOURS_PER_DAY
from mind.services.api import ClockifyAPI


class TimeHoursService:
    """
    Service for displaying monthly summary of logged hours in Clockify.
    Calculates total logged time, maximum possible hours, and prints a summary for a given month.
    """

    def __init__(self) -> None:
        """Initialize the service with console and Clockify API client."""
        self.console = Console()
        self.clockify = ClockifyAPI()

    def show_hours(self, month: int | None = None) -> None:
        """
        Show summary of logged hours for a given month (default: current month).
        Prints total logged, max possible, and summary line.
        """
        today = dt_date.today()
        year = today.year
        month = month or today.month
        start_date = dt_date(year, month, 1)
        end_date = (
            dt_date(year, month + 1, 1) if month < 12 else dt_date(year + 1, 1, 1)
        )
        end_date = end_date - timedelta(days=1)
        entries = self._fetch_entries(start_date, end_date)
        total_seconds = sum_entry_durations(entries)
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        month_name = start_date.strftime("%B")
        max_hours = max_working_hours_in_month(year=year, month=month)
        note = "(PL holidays excluded)"
        self._print_summary(month_name, year, h, m, max_hours, note)

    def _fetch_entries(self, start: dt_date, end: dt_date) -> list[dict]:
        """
        Fetch time entries from Clockify for the given date range.
        """
        start_utc, _ = day_range_utc(start)
        _, end_utc = day_range_utc(end)
        return self.clockify.get_time_entries(start_utc, end_utc)

    def _print_summary(
        self, month_name: str, year: int, h: int, m: int, max_hours: int, note: str
    ) -> None:
        """
        Print the summary of logged and possible hours for the month.
        """
        self._print_total_logged(month_name, year, h, m)
        self._print_max_possible(month_name, year, max_hours, note)
        self._print_missing_hours(h, m, max_hours)
        self._print_summary_line(h, m, max_hours)

    def _print_total_logged(self, month_name: str, year: int, h: int, m: int) -> None:
        """Print total logged hours for the month."""
        logged_str = f"{h}h {m}m" if m else f"{h}h"
        self.console.print(
            f"📆 Total logged in [blue]{month_name} {year}[/blue]: {logged_str}"
        )

    def _print_max_possible(
        self, month_name: str, year: int, max_hours: int, note: str
    ) -> None:
        """Print maximum possible hours for the month."""
        self.console.print(
            f"🕐 Max possible hours in [blue]{month_name} {year}[/blue]: {max_hours}h ({WORKING_HOURS_PER_DAY}h/day) {note}"
        )

    def _print_missing_hours(self, h: int, m: int, max_hours: int) -> None:
        """
        Calculate and print missing hours until reaching the monthly max.
        """
        total_logged_seconds = h * 3600 + m * 60
        max_seconds = max_hours * 3600
        missing_seconds = max_seconds - total_logged_seconds

        if missing_seconds > 0:
            missing_h = missing_seconds // 3600
            missing_m = (missing_seconds % 3600) // 60
            missing_str = f"{missing_h}h {missing_m}m" if missing_m else f"{missing_h}h"
            self.console.print(f"⏱️  Missing hours: [yellow]{missing_str}[/yellow]")
        else:
            self.console.print(f"✅ All hours completed!")

    def _print_summary_line(self, h: int, m: int, max_hours: int) -> None:
        """Print the summary line with color based on completion status."""
        total_logged_hours = h + (m / 60)
        color = "green" if total_logged_hours >= max_hours else "yellow"
        summary_str = f"{h}h {m}m" if m else f"{h}h"
        self.console.print(
            f"📊 Summary: [bold {color}]{summary_str} / {max_hours}h[/bold {color}]"
        )
