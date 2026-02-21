import calendar
import os
from datetime import date as dt_date

from rich.console import Console

from mind.common.utils import max_working_hours_in_month
from mind.config.settings import CLOCKIFY_REPORT_BASE_NAME, CLOCKIFY_REPORT_SAVE_PATH
from mind.services.api import ClockifyAPI


class DownloadReportService:
    """
    Service for generating and downloading monthly reports from Clockify.
    Supports PDF export with confirmation prompt showing total logged hours.
    """

    def __init__(self) -> None:
        """Initialize the service with console and Clockify API client."""
        self.console = Console()
        self.clockify = ClockifyAPI()

    def prepare_report(self, month: int | None = None):
        """
        Prepare data for a monthly PDF report for the given month (default: current).
        Returns: dict with summary, filepath, year, month, total_seconds, max_hours, error (if any)
        """
        today = dt_date.today()
        year = today.year
        month = month or today.month

        start_date = dt_date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = dt_date(year, month, last_day)

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        start_display = start_date.strftime("%d.%m.%Y")
        end_display = end_date.strftime("%d.%m.%Y")
        month_name = start_date.strftime("%B")
        summary = f"🔍 Checking logged hours for [blue]{month_name}[/blue] ({start_display} to {end_display})..."
        self.console.print(summary)
        try:
            total_seconds = self._get_total_seconds(start_str, end_str)
        except Exception as e:
            msg = str(e)
            if "No time entries found" in msg:
                return {
                    "error": f"[yellow]⚠️  No time entries found for {month_name} {year}.[/yellow]"
                }
            elif "still processing" in msg or "API is slow" in msg:
                return {
                    "error": f"[yellow]⏳ Clockify report is still processing or API is slow. Please try again in a moment.[/yellow]"
                }
            else:
                return {"error": f"[red]❌ Error: {e}[/red]"}

        max_hours = max_working_hours_in_month(year=year, month=month)
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        logged_str = f"{h}h {m}m" if m else f"{h}h"
        color = "green" if (h + m / 60) >= max_hours else "yellow"
        hours_summary = f"✅ Total logged hours: [bold {color}]{logged_str} / {max_hours}h[/bold {color}]"
        filepath = self._build_filepath(year, month)
        return {
            "summary": summary,
            "hours_summary": hours_summary,
            "filepath": filepath,
            "year": year,
            "month": month,
            "month_name": month_name,
            "total_seconds": total_seconds,
            "max_hours": max_hours,
        }

    def download_report(self, year: int, month: int, filepath: str) -> None:
        start_date = dt_date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = dt_date(year, month, last_day)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        self.console.print("🚀 Generating the report...")
        self._download_pdf(start_str, end_str, filepath)
        self.console.print(f"✅ PDF report saved as: [green]{filepath}[/green]")

    def _get_total_seconds(self, start_date: str, end_date: str) -> int:
        """Submit a JSON report and extract total logged time in seconds."""
        task_id = self.clockify.submit_summary_report(start_date, end_date)
        report_data = self.clockify.fetch_report_json(task_id)

        total_time = (report_data.get("totals") or [{}])[0].get("totalTime")
        if total_time is None:
            raise RuntimeError("Could not parse totalTime from report data.")

        return total_time

    def _download_pdf(self, start_date: str, end_date: str, filepath: str) -> None:
        """Submit a PDF report request and download the file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        task_id = self.clockify.submit_summary_report(
            start_date, end_date, export_pdf=True
        )
        self.clockify.download_report_pdf(task_id, filepath)

    def _build_filepath(self, year: int, month: int) -> str:
        """Build the output file path for the report."""
        filename = f"{year}-{month:02d} {CLOCKIFY_REPORT_BASE_NAME} - wykaz godzin.pdf"
        if CLOCKIFY_REPORT_SAVE_PATH:
            return os.path.join(CLOCKIFY_REPORT_SAVE_PATH, filename)
        return filename
