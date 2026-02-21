"""
Commands for downloading reports from Clockify.

Includes:
- download report: Download monthly PDF report
"""

import click

from mind.commands.validation import validate_month
from mind.services.download_commands import DownloadReportService


@click.group()
def download():
    """Download-related commands."""
    pass


@download.command("report")
@click.argument("month", required=False, type=int, callback=validate_month)
def report(month: int | None) -> None:
    """
    Download a monthly PDF report from Clockify.

    MONTH: Month number (1-12), defaults to current
    """
    service = DownloadReportService()
    result = service.prepare_report(month)
    if "error" in result:
        service.console.print(result["error"])
        return
    service.console.print(result["hours_summary"])
    service.console.print(
        f"💭 Do you want to generate the PDF report for [blue]{result['month_name']} {result['year']}[/blue]?"
    )
    if not click.confirm(f"⏳ Proceed?"):
        click.echo("❌ Cancelled.")
        return
    service.download_report(result["year"], result["month"], result["filepath"])
