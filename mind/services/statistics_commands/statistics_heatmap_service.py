"""
Service for the statistics heatmap command.

Fetches time entries from Clockify for a given month and renders
a daily hours bar chart directly in the terminal.
"""

from datetime import date as dt_date
from datetime import timedelta

from rich.console import Console

from mind.common.utils import (
    day_range_utc,
    format_duration,
    month_range,
    utc_iso_to_warsaw_local,
)
from mind.services.api import ClockifyAPI

_BAR_MAX_HOURS = 12
_BAR_WIDTH = 20


class StatisticsHeatmapService:
    """
    Service for displaying a daily hours heatmap for a given month.
    Time data comes exclusively from Clockify — no Planner dependency.
    """

    def __init__(self) -> None:
        self.console = Console()
        self.clockify = ClockifyAPI()

    def show_heatmap(self, month: int | None = None) -> None:
        """
        Fetch and display logged hours per day as a bar chart.

        Args:
            month: Month number (1–12). Defaults to the current month.
        """
        start_date, end_date = month_range(month)

        try:
            entries = self._fetch_entries(start_date, end_date)
        except Exception as e:
            self.console.print(f"[red]❌ Error fetching data: {e}[/red]")
            return

        days_data = self._group_by_day(entries, start_date, end_date)
        self._print(start_date, end_date, days_data)

    # ── Data fetching ────────────────────────────────────────────────────────

    def _fetch_entries(self, start: dt_date, end: dt_date) -> list[dict]:
        """Fetch all Clockify time entries for the given date range."""
        start_utc, _ = day_range_utc(start)
        _, end_utc = day_range_utc(end)
        return self.clockify.get_time_entries(start_utc, end_utc)

    # ── Data processing ──────────────────────────────────────────────────────

    def _group_by_day(
        self, entries: list[dict], start: dt_date, end: dt_date
    ) -> dict[dt_date, int]:
        """Return {day: total_logged_seconds} for every day in the range (days with no entries = 0)."""
        totals: dict[dt_date, int] = {
            start + timedelta(days=i): 0 for i in range((end - start).days + 1)
        }
        for entry in entries:
            try:
                interval = entry.get("timeInterval") or {}
                start_str = interval.get("start")
                end_str = interval.get("end")
                if not start_str or not end_str:
                    continue
                start_dt = utc_iso_to_warsaw_local(start_str)
                end_dt = utc_iso_to_warsaw_local(end_str)
                day = start_dt.date()
                if day < start or day > end:
                    continue
                seconds = int((end_dt - start_dt).total_seconds())
                totals[day] += seconds
            except Exception:
                continue
        return totals

    # ── Rendering ────────────────────────────────────────────────────────────

    def _bar(self, seconds: int) -> str:
        """Render a proportional Unicode block bar capped at _BAR_MAX_HOURS."""
        hours = seconds / 3600
        filled = round(min(hours, _BAR_MAX_HOURS) / _BAR_MAX_HOURS * _BAR_WIDTH)
        return "▇" * filled

    def _print(
        self,
        start: dt_date,
        end: dt_date,
        days_data: dict[dt_date, int],
    ) -> None:
        header = f"{start.strftime('%B')} {start.year}"
        self.console.print(f"\n[bold][blue]{header}[/blue][/bold]")
        self.console.print("─" * 48)

        days = [start + timedelta(days=i) for i in range((end - start).days + 1)]

        for day in days:
            seconds = days_data.get(day, 0)
            bar = self._bar(seconds)
            hours_str = format_duration(seconds) if seconds else "0h"

            if seconds == 0:
                bar_col = f"[dim]{' ' * _BAR_WIDTH}[/dim]"
                hours_col = f"[dim]{hours_str}[/dim]"
            elif seconds >= 8 * 3600:
                bar_col = f"[green]{bar:<{_BAR_WIDTH}}[/green]"
                hours_col = f"[green]{hours_str}[/green]"
            else:
                bar_col = f"[yellow]{bar:<{_BAR_WIDTH}}[/yellow]"
                hours_col = f"[yellow]{hours_str}[/yellow]"

            self.console.print(f"{day.strftime('%d-%m-%Y')}  {bar_col}  {hours_col}")
        self.console.print()
