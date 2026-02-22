"""
Service for displaying planned availability from the Planner API.
"""

from collections import defaultdict
from datetime import date as dt_date
from datetime import datetime, timedelta

from rich.console import Console

from mind.common.utils import max_working_hours_in_month
from mind.config.settings import PLANNER_USER_ID
from mind.services.api import PlannerAPI


class PlanShowService:
    def __init__(self) -> None:
        self.console = Console()
        self.planner = PlannerAPI()

    def show(self, month: int | None = None) -> None:
        try:
            start_date, end_date = self._month_range(month)
            raw = self.planner.get_availabilities(
                start_date.isoformat(), end_date.isoformat()
            )
            user = next((u for u in raw if u.get("userId") == PLANNER_USER_ID), None)
            if not user or not user.get("records"):
                self.console.print(
                    "[yellow]No planned availability found for this month.[/yellow]"
                )
                return
            grouped = self._group_by_date(user["records"])
            self._print(grouped)
        except Exception as e:
            self.console.print(
                f"[red]❌ Error fetching planned availability: {e}[/red]"
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _month_range(self, month: int | None) -> tuple[dt_date, dt_date]:
        today = dt_date.today()
        m = month or today.month
        y = today.year
        first = dt_date(y, m, 1)
        last = (dt_date(y, m + 1, 1) if m < 12 else dt_date(y + 1, 1, 1)) - timedelta(
            days=1
        )
        return first, last

    def _group_by_date(self, records: list[dict]) -> dict[dt_date, list[dict]]:
        grouped: dict[dt_date, list[dict]] = defaultdict(list)
        for entry in records:
            try:
                day = dt_date.fromisoformat(entry["start"][:10])
            except (KeyError, ValueError):
                continue
            grouped[day].append(entry)
        # Newest day first
        return dict(sorted(grouped.items(), reverse=True))

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _format_hours(total_seconds: int) -> str:
        h, rem = divmod(total_seconds, 3600)
        m = rem // 60
        return f"{h}h {m}m" if m else f"{h}h"

    def _print(self, grouped: dict[dt_date, list[dict]]) -> None:
        if not grouped:
            self.console.print(
                "[yellow]No planned availability found for this month.[/yellow]"
            )
            return

        # Build rows first so we can measure max hours width for alignment
        rows: list[tuple[dt_date, int, list[str]]] = []
        for day, entries in grouped.items():
            total_seconds = 0
            intervals: list[str] = []
            for entry in entries:
                try:
                    s = self._parse_dt(entry["start"])
                    e = self._parse_dt(entry["end"])
                except (KeyError, ValueError):
                    continue
                total_seconds += max(0, int((e - s).total_seconds()))
                mode = entry.get("workplaceName") or entry.get("status") or ""
                part = f"{s.strftime('%H:%M')}–{e.strftime('%H:%M')} {mode}".strip()
                intervals.append(part)
            rows.append((day, total_seconds, intervals))

        col_width = max(len(self._format_hours(r[1])) for r in rows)

        for day, total_seconds, intervals in rows:
            hours_str = self._format_hours(total_seconds).ljust(col_width)
            detail = f"  [dim]({', '.join(intervals)})[/dim]" if intervals else ""
            self.console.print(
                f"{day.strftime('%d.%m.%Y')}  Planned: [cyan]{hours_str}[/cyan]{detail}"
            )

        # Summary line
        if rows:
            self._print_summary(rows, col_width)

    def _print_summary(self, rows, col_width):
        self.console.print("─" * (col_width + 30))
        total_planned = sum(r[1] for r in rows)
        month = rows[0][0].month
        year = rows[0][0].year
        max_hours = max_working_hours_in_month(year, month)
        self.console.print(
            f"Total planned: [cyan]{self._format_hours(total_planned)} / {max_hours}h[/cyan]"
        )
