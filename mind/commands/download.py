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
    DownloadReportService().generate_report(month)
