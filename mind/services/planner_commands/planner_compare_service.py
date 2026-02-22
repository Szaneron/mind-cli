"""
Service for comparing planned availability vs logged Clockify hours per day.
"""

from collections import defaultdict
from datetime import date as dt_date
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from rich.console import Console

from mind.config.settings import PLANNER_USER_ID
from mind.services.api import ClockifyAPI, PlannerAPI

WARSAW_TZ = ZoneInfo("Europe/Warsaw")


class PlanCompareService:
    def __init__(self) -> None:
        self.console = Console()
        self.planner = PlannerAPI()
        self.clockify = ClockifyAPI()

    def compare(self, month: int | None = None) -> None:
        try:
            start_date, end_date = self._month_range(month)
            planned = self._fetch_planned(start_date, end_date)
            logged = self._fetch_logged(start_date, end_date)

            if not planned:
                self.console.print(
                    "[yellow]No planned availability found for this month.[/yellow]"
                )
                return

            self._print(planned, logged)
        except Exception as e:
            self.console.print(f"[red]❌ Error comparing hours: {e}[/red]")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _month_range(self, month: int | None) -> tuple[dt_date, dt_date]:
        from datetime import date as dt_date

        today = dt_date.today()
        m = month or today.month
        y = today.year
        first = dt_date(y, m, 1)
        last = (dt_date(y, m + 1, 1) if m < 12 else dt_date(y + 1, 1, 1)) - timedelta(
            days=1
        )
        return first, last

    def _fetch_planned(self, start: dt_date, end: dt_date) -> dict[dt_date, int]:
        """Return {day: total_planned_seconds} for PLANNER_USER_ID."""
        raw = self.planner.get_availabilities(start.isoformat(), end.isoformat())
        user = next((u for u in raw if u.get("userId") == PLANNER_USER_ID), None)
        if not user or not user.get("records"):
            return {}

        totals: dict[dt_date, int] = defaultdict(int)
        for entry in user["records"]:
            try:
                s = datetime.fromisoformat(entry["start"].replace("Z", "+00:00"))
                e = datetime.fromisoformat(entry["end"].replace("Z", "+00:00"))
                day = s.astimezone(WARSAW_TZ).date()
                totals[day] += max(0, int((e - s).total_seconds()))
            except (KeyError, ValueError):
                continue
        return dict(totals)

    def _fetch_logged(self, start: dt_date, end: dt_date) -> dict[dt_date, int]:
        """Return {day: total_logged_seconds} from Clockify."""
        start_utc = datetime.combine(
            start, datetime.min.time(), tzinfo=WARSAW_TZ
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_utc = datetime.combine(
            end, datetime.max.time().replace(microsecond=0), tzinfo=WARSAW_TZ
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
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
        h, rem = divmod(total_seconds, 3600)
        m = rem // 60
        return f"{h}h {m}m" if m else f"{h}h"

    def _print(self, planned: dict[dt_date, int], logged: dict[dt_date, int]) -> None:
        # Only show days that have planned hours, newest first
        days = sorted(planned.keys(), reverse=True)

        # Pre-build all row data to determine column widths
        rows = []
        for day in days:
            p_sec = planned[day]
            l_sec = logged.get(day, 0)
            diff = l_sec - p_sec

            p_str = self._fmt(p_sec)
            l_str = self._fmt(l_sec)

            if diff == 0:
                diff_str = "OK"
                diff_style = "green"
            elif diff > 0:
                diff_str = f"+{self._fmt(diff)}"
                diff_style = "yellow"
            else:
                diff_str = f"Missing: {self._fmt(abs(diff))}"
                diff_style = "red"

            rows.append((day, p_str, l_str, diff_str, diff_style))

        # Calculate column widths for alignment
        date_w = max(len(d.strftime("%d.%m.%Y")) for d, *_ in rows)
        plan_w = max(len(r[1]) for r in rows)
        log_w = max(len(r[2]) for r in rows)

        for day, p_str, l_str, diff_str, diff_style in rows:
            date_col = day.strftime("%d.%m.%Y").ljust(date_w)
            plan_col = p_str.ljust(plan_w)
            log_col = l_str.ljust(log_w)
            self.console.print(
                f"{date_col}  Planned: [cyan]{plan_col}[/cyan]  "
                f"Logged: [blue]{log_col}[/blue]  "
                f"[{diff_style}]{diff_str}[/{diff_style}]"
            )

        # Summary line
        if rows:
            self._print_summary(planned, logged, rows, date_w, plan_w, log_w)

    def _print_summary(self, planned, logged, rows, date_w, plan_w, log_w):
        self.console.print("─" * (date_w + plan_w + log_w + 40))
        total_planned = sum(planned.values())
        total_logged = sum(logged.get(day, 0) for day in planned)
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
