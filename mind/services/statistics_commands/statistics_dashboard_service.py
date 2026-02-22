"""
Service for the stats dashboard command.

Fetches time entries from Clockify and planned availability from the Planner
for a given month, then renders:
- Time summary (logged / planned / difference)
- Office vs Remote ratio (derived from Planner workplaceName)
- Stability (consistency, aligned/under/overtime days)
- Highlights (most overtime day, most missing day)
- Average hours per day
"""

from dataclasses import dataclass
from datetime import date as dt_date
from datetime import datetime
from zoneinfo import ZoneInfo

from rich.console import Console

from mind.common.utils import (
    day_range_utc,
    format_duration,
    month_range,
    utc_iso_to_warsaw_local,
)
from mind.config.settings import PLANNER_USER_ID
from mind.services.api import ClockifyAPI, PlannerAPI

_REMOTE_WORKPLACE = "remote"
_STATUS_NOT_AVAILABLE = "notavailable"
_BAR_WIDTH = 21
_WARSAW_TZ = ZoneInfo("Europe/Warsaw")


@dataclass
class StatsSnapshot:
    """All computed statistics for a single month."""

    month_name: str
    year: int
    logged_s: int
    planned_s: int
    diff_s: int
    office_pct: int
    remote_pct: int
    consistency_pct: int
    aligned: int
    under: int
    over: int
    overall_label: str
    longest_day: dt_date | None
    longest_s: int
    longest_range: str
    longest_break_s: int
    shortest_day: dt_date | None
    shortest_s: int
    shortest_range: str
    shortest_break_s: int
    avg_s: int


class StatisticsDashboardService:
    """
    Service for displaying the monthly statistics dashboard.
    Time data comes from Clockify; office/remote ratio comes from the Planner.
    Supports full dashboard view and compact single-line view.
    """

    def __init__(self) -> None:
        """Initialize the service with console, Clockify and Planner API clients."""
        self.console = Console()
        self.clockify = ClockifyAPI()
        self.planner = PlannerAPI()

    def show_stats(self, month: int | None = None, compact: bool = False) -> None:
        """
        Compute and display monthly statistics.

        Args:
            month: Month number (1–12). Defaults to the current month.
            compact: If True, print a single summary line instead of the full dashboard.
        """
        start_date, end_date = month_range(month)

        try:
            entries = self._fetch_clockify_entries(start_date, end_date)
            planner_records = self._fetch_planner_records(start_date, end_date)
        except Exception as e:
            self.console.print(f"[red]❌ Error fetching data: {e}[/red]")
            return

        planned_by_day = self._planned_by_day(planner_records)
        days_data = self._group_by_day(entries, start_date, end_date)
        snapshot = self._build_snapshot(
            start_date, days_data, planned_by_day, planner_records
        )

        if compact:
            self._print_compact(snapshot)
        else:
            self._print_dashboard(snapshot)

    # ── Data fetching ────────────────────────────────────────────────────────

    def _fetch_clockify_entries(self, start: dt_date, end: dt_date) -> list[dict]:
        """Fetch all Clockify time entries for the given date range."""
        start_utc, _ = day_range_utc(start)
        _, end_utc = day_range_utc(end)
        return self.clockify.get_time_entries(start_utc, end_utc)

    def _fetch_planner_records(self, start: dt_date, end: dt_date) -> list[dict]:
        """Fetch active working Planner records for the current user (excludes notAvailable)."""
        raw = self.planner.get_availabilities(start.isoformat(), end.isoformat())
        user = next((u for u in raw if u.get("userId") == PLANNER_USER_ID), None)
        if not user:
            return []
        return [
            r
            for r in (user.get("records") or [])
            if r.get("active") and r.get("status", "").lower() != _STATUS_NOT_AVAILABLE
        ]

    def _planned_by_day(self, records: list[dict]) -> dict[dt_date, int]:
        """Return {day: total_planned_seconds} from Planner records."""
        totals: dict[dt_date, int] = {}
        for r in records:
            try:
                start_dt = datetime.fromisoformat(r["start"].replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(r["end"].replace("Z", "+00:00"))
                day = start_dt.astimezone(_WARSAW_TZ).date()
                seconds = max(0, int((end_dt - start_dt).total_seconds()))
                totals[day] = totals.get(day, 0) + seconds
            except Exception:
                continue
        return totals

    # ── Data processing ──────────────────────────────────────────────────────

    def _group_by_day(
        self,
        entries: list[dict],
        start: dt_date,
        end: dt_date,
    ) -> dict[dt_date, dict]:
        """
        Group Clockify entries by date, accumulating seconds per day.
        Only days with at least one valid (completed) entry are included.
        """
        result: dict[dt_date, dict] = {}
        for entry in entries:
            try:
                interval = entry.get("timeInterval") or {}
                start_str = interval.get("start")
                end_str = interval.get("end")
                if not start_str or not end_str:
                    continue

                start_dt = utc_iso_to_warsaw_local(start_str)
                end_dt = utc_iso_to_warsaw_local(end_str)
                entry_date = start_dt.date()

                if entry_date < start or entry_date > end:
                    continue

                seconds = int((end_dt - start_dt).total_seconds())
                if entry_date not in result:
                    result[entry_date] = {
                        "seconds": 0,
                        "hours": 0.0,
                        "first_start": start_dt,
                        "last_end": end_dt,
                    }
                else:
                    if start_dt < result[entry_date]["first_start"]:
                        result[entry_date]["first_start"] = start_dt
                    if end_dt > result[entry_date]["last_end"]:
                        result[entry_date]["last_end"] = end_dt
                result[entry_date]["seconds"] += seconds
            except Exception:
                continue

        for day in result:
            result[day]["hours"] = result[day]["seconds"] / 3600

        return result

    def _compute_workplace_ratio(self, records: list[dict]) -> tuple[int, int]:
        """Return (office_pct, remote_pct) from Planner records."""
        office_s = 0.0
        remote_s = 0.0
        for record in records:
            try:
                start_dt = datetime.fromisoformat(
                    record["start"].replace("Z", "+00:00")
                )
                end_dt = datetime.fromisoformat(record["end"].replace("Z", "+00:00"))
                seconds = (end_dt - start_dt).total_seconds()
                if record.get("workplaceName", "").lower() == _REMOTE_WORKPLACE:
                    remote_s += seconds
                else:
                    office_s += seconds
            except Exception:
                continue
        total = office_s + remote_s
        office_pct = round(office_s / total * 100) if total > 0 else 0
        remote_pct = 100 - office_pct if total > 0 else 0
        return office_pct, remote_pct

    def _compute_stability(
        self,
        days_data: dict[dt_date, dict],
        planned_by_day: dict[dt_date, int],
    ) -> tuple[int, int, int, int]:
        """Return (aligned, under, over, consistency_pct) against planned days."""
        working_day_count = len(planned_by_day)
        aligned = sum(
            1
            for day, plan_s in planned_by_day.items()
            if days_data.get(day, {}).get("seconds", 0) == plan_s
        )
        under = sum(
            1
            for day, plan_s in planned_by_day.items()
            if days_data.get(day, {}).get("seconds", 0) < plan_s
        )
        over = sum(
            1
            for day, plan_s in planned_by_day.items()
            if days_data.get(day, {}).get("seconds", 0) > plan_s
        )
        consistency_pct = (
            round(aligned / working_day_count * 100) if working_day_count > 0 else 0
        )
        return aligned, under, over, consistency_pct

    def _highlight_logged_extremes(
        self,
        days_data: dict[dt_date, dict],
    ) -> tuple[tuple, tuple]:
        """Return (longest_day_tuple, shortest_day_tuple) for days with logged time."""
        if not days_data:
            return (None, 0, "", 0), (None, 0, "", 0)

        nonzero = [
            (day, data["seconds"], data.get("first_start"), data.get("last_end"))
            for day, data in days_data.items()
            if data["seconds"] > 0
        ]
        if not nonzero:
            return (None, 0, "", 0), (None, 0, "", 0)

        def fmt_range(start, end) -> str:
            return (
                f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"
                if start and end
                else ""
            )

        def break_seconds(logged: int, start, end) -> int:
            return (
                max(0, int((end - start).total_seconds()) - logged)
                if start and end
                else 0
            )

        def build_tuple(entry: tuple) -> tuple:
            day, logged, start, end = entry
            return day, logged, fmt_range(start, end), break_seconds(logged, start, end)

        return (
            build_tuple(max(nonzero, key=lambda x: x[1])),
            build_tuple(min(nonzero, key=lambda x: x[1])),
        )

    def _build_snapshot(
        self,
        start_date: dt_date,
        days_data: dict[dt_date, dict],
        planned_by_day: dict[dt_date, int],
        planner_records: list[dict],
    ) -> StatsSnapshot:
        """Compute all statistics and return a StatsSnapshot."""
        total_logged_s = sum(d["seconds"] for d in days_data.values())
        total_planned_s = sum(planned_by_day.values())

        office_pct, remote_pct = self._compute_workplace_ratio(planner_records)
        aligned, under, over, consistency_pct = self._compute_stability(
            days_data, planned_by_day
        )

        (longest_day, longest_s, longest_range, longest_break_s), (
            shortest_day,
            shortest_s,
            shortest_range,
            shortest_break_s,
        ) = self._highlight_logged_extremes(days_data)

        logged_day_count = len(days_data)
        avg_s = total_logged_s // logged_day_count if logged_day_count > 0 else 0

        return StatsSnapshot(
            month_name=start_date.strftime("%B"),
            year=start_date.year,
            logged_s=total_logged_s,
            planned_s=total_planned_s,
            diff_s=total_logged_s - total_planned_s,
            office_pct=office_pct,
            remote_pct=remote_pct,
            consistency_pct=consistency_pct,
            aligned=aligned,
            under=under,
            over=over,
            overall_label=self._overall_label(consistency_pct),
            longest_day=longest_day,
            longest_s=longest_s,
            longest_range=longest_range,
            longest_break_s=longest_break_s,
            shortest_day=shortest_day,
            shortest_s=shortest_s,
            shortest_range=shortest_range,
            shortest_break_s=shortest_break_s,
            avg_s=avg_s,
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt(seconds: int) -> str:
        return format_duration(seconds)

    @staticmethod
    def _fmt_diff(diff_seconds: int) -> str:
        """Format a signed diff in seconds as '+Xh Ym', '-Xh Ym' or '+0h'."""
        sign = "+" if diff_seconds >= 0 else "-"
        return f"{sign}{format_duration(diff_seconds)}"

    @staticmethod
    def _overall_label(consistency_pct: int) -> str:
        if consistency_pct >= 80:
            return "[green]🎯 Consistent[/green]"
        elif consistency_pct >= 60:
            return "[cyan]⚖️ Balanced[/cyan]"
        else:
            return "[red]⚠️  Unstable[/red]"

    def _bar(self, pct: int) -> str:
        """Render a Unicode block progress bar."""
        if pct == 0:
            return ""
        filled = round(pct / 100 * _BAR_WIDTH)
        return "█" * filled + " " * (_BAR_WIDTH - filled)

    def _fmt_highlight_day(
        self, day: dt_date, logged_s: int, time_range: str, break_s: int, color: str
    ) -> str:
        """Format a single highlight line (longest/shortest day)."""
        range_str = f"  {time_range}" if time_range else ""
        break_str = (
            f"  [dim]({self._fmt(break_s)} break)[/dim]" if break_s > 15 * 60 else ""
        )
        return (
            f"[cyan]{day.strftime('%d.%m.%Y')}[/cyan]"
            f" [{color}]{self._fmt(logged_s)}[/{color}]"
            f"[dim]{range_str}[/dim]{break_str}"
        )

    # ── Rendering ────────────────────────────────────────────────────────────

    def _print_dashboard(self, snap: StatsSnapshot) -> None:
        c = self.console
        c.print(f"\nMonth: [blue][bold]{snap.month_name} {snap.year}[/bold][/blue]")
        c.print("─" * 40)
        self._render_time(snap)
        self._render_workplace(snap)
        self._render_stability(snap)
        self._render_highlights(snap)
        self._render_average(snap)

    def _render_time(self, snap: StatsSnapshot) -> None:
        diff_color = "green" if snap.diff_s >= 0 else "red"
        c = self.console
        c.print("\n[bold][blue]Time[/blue][/bold]")
        c.print(f"  Logged:     [cyan]{self._fmt(snap.logged_s)}[/cyan]")
        c.print(f"  Planned:    [cyan]{self._fmt(snap.planned_s)}[/cyan]")
        c.print(
            f"  Difference: [{diff_color}]{self._fmt_diff(snap.diff_s)}[/{diff_color}]"
        )

    def _render_workplace(self, snap: StatsSnapshot) -> None:
        c = self.console
        c.print("\n[bold][blue]Office vs Remote[/blue][/bold]")
        c.print(
            f"  Office  {self._bar(snap.office_pct)}  [cyan]{snap.office_pct}%[/cyan]"
        )
        c.print(
            f"  Remote  {self._bar(snap.remote_pct)}  [green]{snap.remote_pct}%[/green]"
        )

    def _render_stability(self, snap: StatsSnapshot) -> None:
        c = self.console
        c.print("\n[bold][blue]Stability[/blue][/bold]")
        c.print(f"  Consistency: [bold][cyan]{snap.consistency_pct}%[/cyan][/bold]")
        c.print(
            f"    {snap.aligned} day{'s' if snap.aligned != 1 else ''} met the plan"
        )
        c.print(
            f"    {snap.under} day{'s' if snap.under != 1 else ''} below planned time"
        )
        c.print(
            f"    {snap.over} day{'s' if snap.over != 1 else ''} above planned time"
        )
        c.print(f"  Overall: {snap.overall_label}")

    def _render_highlights(self, snap: StatsSnapshot) -> None:
        c = self.console
        c.print("\n[bold][blue]Highlights[/blue][/bold]")
        if snap.longest_day:
            c.print(
                "  Longest:  "
                + self._fmt_highlight_day(
                    snap.longest_day,
                    snap.longest_s,
                    snap.longest_range,
                    snap.longest_break_s,
                    "red",
                )
            )
        else:
            c.print("  Longest:  —")
        if snap.shortest_day:
            c.print(
                "  Shortest: "
                + self._fmt_highlight_day(
                    snap.shortest_day,
                    snap.shortest_s,
                    snap.shortest_range,
                    snap.shortest_break_s,
                    "yellow",
                )
            )
        else:
            c.print("  Shortest: —")

    def _render_average(self, snap: StatsSnapshot) -> None:
        c = self.console
        c.print("\n[bold][blue]Average[/blue][/bold]")
        c.print(f"  Avg logged per day: [cyan]{self._fmt(snap.avg_s)}[/cyan]")
        c.print()

    def _print_compact(self, snap: StatsSnapshot) -> None:
        diff_color = "green" if snap.diff_s >= 0 else "red"
        self.console.print(
            f"[bold][blue]{snap.month_name[:3]} {snap.year}[/blue][/bold] | "
            f"[cyan]{self._fmt(snap.logged_s)} / {self._fmt(snap.planned_s)}[/cyan] | "
            f"[{diff_color}]{self._fmt_diff(snap.diff_s)}[/{diff_color}] | "
            f"O: [cyan][bold]{snap.office_pct}%[/bold][/cyan] R: [green][bold]{snap.remote_pct}%[/bold][/green] | "
            f"Consistency: [cyan][bold]{snap.consistency_pct}%[/bold][/cyan] | "
            f"{snap.overall_label} | "
            f"Avg logged: [magenta]{self._fmt(snap.avg_s)}[/magenta]"
        )
