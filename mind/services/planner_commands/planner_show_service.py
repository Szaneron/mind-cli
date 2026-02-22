"""
Service for displaying planned availability from the Planner API.
"""

from collections import defaultdict
from datetime import date as dt_date
from datetime import datetime

from rich.console import Console

from mind.common.utils import format_duration, max_working_hours_in_month, month_range
from mind.config.settings import PLANNER_USER_ID
from mind.services.api import PlannerAPI

_STATUS_NOT_AVAILABLE = "notavailable"


class PlanShowService:
    def __init__(self) -> None:
        self.console = Console()
        self.planner = PlannerAPI()

    def show(self, month: int | None = None) -> None:
        try:
            start_date, end_date = month_range(month)
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

    def _print(self, grouped: dict[dt_date, list[dict]]) -> None:
        if not grouped:
            self.console.print(
                "[yellow]No planned availability found for this month.[/yellow]"
            )
            return

        # (day, work_seconds, intervals, has_work)
        rows: list[tuple[dt_date, int, list[str], bool]] = []
        for day, entries in grouped.items():
            work_seconds = 0
            intervals: list[str] = []
            has_work = False
            for entry in entries:
                try:
                    s = self._parse_dt(entry["start"])
                    e = self._parse_dt(entry["end"])
                except (KeyError, ValueError):
                    continue
                duration = max(0, int((e - s).total_seconds()))
                status = entry.get("status", "")
                if status.lower() == _STATUS_NOT_AVAILABLE:
                    mode = "Not Available"
                else:
                    mode = entry.get("workplaceName") or status
                    work_seconds += duration
                    has_work = True
                part = f"{s.strftime('%H:%M')}–{e.strftime('%H:%M')} {mode}".strip()
                intervals.append(part)
            rows.append((day, work_seconds, intervals, has_work))

        work_rows = [r for r in rows if r[3]]
        col_width = max((len(format_duration(r[1])) for r in work_rows), default=4)

        # Calculate max length for the left part (date + label + hours) for alignment
        left_parts = []
        for day, work_seconds, intervals, has_work in rows:
            if has_work:
                hours_str = format_duration(work_seconds).ljust(col_width)
                left = f"{day.strftime('%d.%m.%Y')}  Planned: {hours_str}"
            else:
                left = f"{day.strftime('%d.%m.%Y')}  Not Available"
            left_parts.append(left)
        max_left_len = max((len(lp) for lp in left_parts), default=0)

        for idx, (day, work_seconds, intervals, has_work) in enumerate(rows):
            detail = f"({', '.join(intervals)})" if intervals else ""
            left = left_parts[idx].ljust(max_left_len)
            if has_work:
                self.console.print(f"{left}  [dim]{detail}[/dim]")
            else:
                self.console.print(f"[dim]{left}  {detail}[/dim]")

        if rows:
            self._print_summary(rows, col_width)

    def _print_summary(self, rows, col_width):
        self.console.print("─" * (col_width + 30))
        total_planned = sum(r[1] for r in rows)  # r[1] = work_seconds only
        month = rows[0][0].month
        year = rows[0][0].year
        max_hours = max_working_hours_in_month(year, month)
        self.console.print(
            f"Total planned: [cyan]{format_duration(total_planned)} / {max_hours}h[/cyan]"
        )
