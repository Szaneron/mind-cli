from datetime import date as dt_date
from datetime import timedelta

import holidays
from rich.console import Console

from mind.common.utils import day_range_utc, utc_iso_to_warsaw_local
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
        self.working_hours_per_day = WORKING_HOURS_PER_DAY
        self.country = "PL"

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
        total_seconds = self._sum_entry_durations(entries)
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        month_name = start_date.strftime("%B")
        max_hours = self._max_working_hours_in_month(year, month)
        note = "(PL holidays excluded)"
        self._print_summary(month_name, year, h, m, max_hours, note)

    def _fetch_entries(self, start: dt_date, end: dt_date) -> list[dict]:
        """
        Fetch time entries from Clockify for the given date range.
        """
        user_id = self.clockify.get_user_id()
        start_utc, _ = day_range_utc(start)
        _, end_utc = day_range_utc(end)
        return self.clockify.get_time_entries(user_id, start_utc, end_utc)

    def _sum_entry_durations(self, entries: list[dict]) -> int:
        """
        Sum the durations of all time entries in seconds.
        """
        total = 0
        for entry in entries:
            try:
                start = entry["timeInterval"]["start"]
                end = entry["timeInterval"]["end"]
                start_dt = utc_iso_to_warsaw_local(start)
                end_dt = utc_iso_to_warsaw_local(end)
                total += int((end_dt - start_dt).total_seconds())
            except Exception:
                pass
        return total

    def _max_working_hours_in_month(self, year: int, month: int) -> int:
        """
        Calculate the maximum possible working hours in a month, excluding holidays and weekends.
        """
        pl_holidays = holidays.country_holidays(self.country, years=[year])
        first = dt_date(year, month, 1)
        last = (
            dt_date(year, month + 1, 1) - timedelta(days=1)
            if month < 12
            else dt_date(year + 1, 1, 1) - timedelta(days=1)
        )
        working_days = sum(
            1
            for d in range((last - first).days + 1)
            if dt_date(year, month, 1) + timedelta(days=d) not in pl_holidays
            and (first + timedelta(days=d)).weekday() < 5
        )
        return working_days * self.working_hours_per_day

    def _print_summary(
        self, month_name: str, year: int, h: int, m: int, max_hours: int, note: str
    ) -> None:
        """
        Print the summary of logged and possible hours for the month.
        """
        if m == 0:
            logged_str = f"{h}h"
        else:
            logged_str = f"{h}h {m}m"
        self.console.print(
            f"📆 Total logged in [blue]{month_name} {year}[/blue]: {logged_str}"
        )
        self.console.print(
            f"🕐 Max possible hours in [blue]{month_name} {year}[/blue]: {max_hours}h ({self.working_hours_per_day}h/day) {note}"
        )
        total_logged_hours = h + (m / 60)
        if total_logged_hours >= max_hours:
            color = "green"
        else:
            color = "yellow"
        if m == 0:
            summary_str = f"{h}h"
        else:
            summary_str = f"{h}h {m}m"
        self.console.print(
            f"📊 Summary: [bold {color}]{summary_str} / {max_hours}h[/bold {color}]"
        )
