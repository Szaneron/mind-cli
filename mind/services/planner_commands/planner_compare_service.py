"""
Service for comparing planned availability vs logged Clockify hours per day.
"""

from collections import defaultdict
from datetime import date as dt_date
from datetime import datetime
from zoneinfo import ZoneInfo

from rich.console import Console

from mind.common.utils import day_range_utc, format_duration, month_range
from mind.config.settings import PLANNER_USER_ID
from mind.services.api import ClockifyAPI, PlannerAPI

WARSAW_TZ = ZoneInfo("Europe/Warsaw")
_STATUS_NOT_AVAILABLE = "notavailable"


class PlanCompareService:
    def __init__(self) -> None:
        self.console = Console()
        self.planner = PlannerAPI()
        self.clockify = ClockifyAPI()

    def compare(self, month: int | None = None) -> None:
        try:
            start_date, end_date = month_range(month)
            planned, not_available = self._fetch_planned(start_date, end_date)
            logged = self._fetch_logged(start_date, end_date)

            if not planned and not not_available:
                self.console.print(
                    "[yellow]No planned availability found for this month.[/yellow]"
                )
                return

            self._print(planned, not_available, logged)
        except Exception as e:
            self.console.print(f"[red]❌ Error comparing hours: {e}[/red]")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_planned(
        self, start: dt_date, end: dt_date
    ) -> tuple[dict[dt_date, int], dict[dt_date, int]]:
        """Return ({day: planned_seconds}, {day: planned_seconds_for_not_available_days})."""
        raw = self.planner.get_availabilities(start.isoformat(), end.isoformat())
        user = next((u for u in raw if u.get("userId") == PLANNER_USER_ID), None)
        if not user or not user.get("records"):
            return {}, {}

        totals: dict[dt_date, int] = defaultdict(int)
        not_available: dict[dt_date, int] = defaultdict(int)
        for entry in user["records"]:
            try:
                s = datetime.fromisoformat(entry["start"].replace("Z", "+00:00"))
                e = datetime.fromisoformat(entry["end"].replace("Z", "+00:00"))
                day = s.astimezone(WARSAW_TZ).date()
                duration = max(0, int((e - s).total_seconds()))
            except (KeyError, ValueError):
                continue
            if entry.get("status", "").lower() == _STATUS_NOT_AVAILABLE:
                not_available[day] += duration
            else:
                totals[day] += duration
        return dict(totals), dict(not_available)

    def _fetch_logged(self, start: dt_date, end: dt_date) -> dict[dt_date, int]:
        """Return {day: total_logged_seconds} from Clockify."""
        start_utc, _ = day_range_utc(start)
        _, end_utc = day_range_utc(end)
        entries = self.clockify.get_time_entries(start_utc, end_utc)

        totals: dict[dt_date, int] = defaultdict(int)
        for entry in entries:
            interval = entry.get("timeInterval") or {}
            s_raw = interval.get("start")
            e_raw = interval.get("end")
            if not s_raw or not e_raw:
                continue
            try:
                s = datetime.fromisoformat(s_raw.replace("Z", "+00:00")).astimezone(
                    WARSAW_TZ
                )
                e = datetime.fromisoformat(e_raw.replace("Z", "+00:00")).astimezone(
                    WARSAW_TZ
                )
                totals[s.date()] += max(0, int((e - s).total_seconds()))
            except (TypeError, ValueError):
                continue
        return dict(totals)

    @staticmethod
    def _fmt(total_seconds: int) -> str:
        return format_duration(total_seconds)

    def _print(
        self,
        planned: dict[dt_date, int],
        not_available: dict[dt_date, int],
        logged: dict[dt_date, int],
    ) -> None:
        # All days: working + not-available, newest first
        all_days = sorted(set(planned) | set(not_available), reverse=True)

        # Pre-build row data: (day, p_str, l_str, diff_str, diff_style, is_not_available)
        rows = []
        for day in all_days:
            is_na = day in not_available and day not in planned
            p_sec = planned.get(day, not_available.get(day, 0))
            l_sec = logged.get(day, 0)

            p_str = self._fmt(p_sec) if p_sec else "Not Available"
            l_str = self._fmt(l_sec)

            if is_na:
                # If there are logged hours on a not-available day, show 'Own day off' in diff column
                if l_sec > 0:
                    diff_str = "Own day off"
                elif p_sec > 0 and l_sec == 0:
                    diff_str = "Day off"
                else:
                    diff_str = ""
                rows.append((day, p_str, l_str, diff_str, "", True))
            else:
                diff = l_sec - p_sec
                # If planned is 0 (not not-available) but logged > 0, show 'Day off'
                if p_sec == 0 and l_sec > 0:
                    diff_str, diff_style = "Day off", "yellow"
                elif p_sec > 0 and l_sec == 0:
                    diff_str, diff_style = "Day off", "yellow"
                elif diff == 0:
                    diff_str, diff_style = "OK", "green"
                elif diff > 0:
                    diff_str, diff_style = f"+{self._fmt(diff)}", "yellow"
                else:
                    diff_str, diff_style = f"Missing: {self._fmt(abs(diff))}", "red"
                rows.append((day, p_str, l_str, diff_str, diff_style, False))

        # Column widths (based on all rows)
        date_w = max(len(d.strftime("%d.%m.%Y")) for d, *_ in rows)
        plan_w = max(len(r[1]) for r in rows)
        log_w = max(len(r[2]) for r in rows)

        for day, p_str, l_str, diff_str, diff_style, is_na in rows:
            date_col = day.strftime("%d.%m.%Y").ljust(date_w)
            plan_col = p_str.ljust(plan_w)
            log_col = l_str.ljust(log_w)
            if is_na:
                # Show 'Dzień wolny' in diff column if present
                if diff_str:
                    self.console.print(
                        f"[dim]{date_col}  Planned: {plan_col}  "
                        f"Logged: {log_col}  {diff_str}[/dim]"
                    )
                else:
                    self.console.print(
                        f"[dim]{date_col}  Planned: {plan_col}  "
                        f"Logged: {log_col}[/dim]"
                    )
            else:
                self.console.print(
                    f"{date_col}  Planned: [cyan]{plan_col}[/cyan]  "
                    f"Logged: [blue]{log_col}[/blue]  "
                    f"[{diff_style}]{diff_str}[/{diff_style}]"
                )

        # Summary line (working days only)
        if any(not r[5] for r in rows):
            self._print_summary(planned, logged, rows, date_w, plan_w, log_w)

    def _print_summary(self, planned, logged, rows, date_w, plan_w, log_w):
        self.console.print("─" * (date_w + plan_w + log_w + 40))
        # Only count working (non-not-available) days
        working_days = {r[0] for r in rows if not r[5]}
        total_planned = sum(planned.get(day, 0) for day in working_days)
        total_logged = sum(logged.get(day, 0) for day in working_days)
        mismatch = total_logged - total_planned
        if mismatch == 0:
            mismatch_str = "OK"
            mismatch_style = "green"
        elif mismatch > 0:
            mismatch_str = f"+{self._fmt(mismatch)}"
            mismatch_style = "yellow"
        else:
            mismatch_str = f"Missing: {self._fmt(abs(mismatch))}"
            mismatch_style = "red"
        self.console.print(
            f"Total planned: [cyan]{self._fmt(total_planned)}[/cyan]    "
            f"Total logged: [blue]{self._fmt(total_logged)}[/blue]    "
            f"[{mismatch_style}]{mismatch_str}[/{mismatch_style}]"
        )
