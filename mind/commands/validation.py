import click


def validate_issue_key(ctx, param, value):
    """
    Validate issue key (PEG-123 or peg-123).
    Accepts uppercase/lowercase, must match PEG-<digits>.
    """
    import re

    if value is None:
        return value
    if not re.match(r"^peg-\d+$", value.lower()):
        raise click.BadParameter(
            click.style(
                "❌ Issue key must be in format PEG-123 (case-insensitive)", fg="red"
            )
        )
    return value.upper()


def validate_date(ctx, param, value):
    """
    Validate and parse date argument for CLI commands using parse_day_and_month from utils.
    Returns a dt_date object or today's date if None.
    """
    try:
        from mind.common.utils import parse_day_and_month

        return parse_day_and_month(value)
    except Exception:
        raise click.BadParameter(
            click.style(
                "❌ Invalid date format. Acceptable: DD.MM.YYYY, DD.MM, DD", fg="red"
            )
        )


def validate_time_period(ctx, param, value):
    """
    Validate time period argument (e.g. '9-17' or '9:30-12:45').
    """
    if value is None:
        return value
    parts = value.split("-")
    if len(parts) != 2:
        raise click.BadParameter(
            click.style(
                "❌ Time period must be in format HH-HH or HH:MM-HH:MM (e.g. 9-17 or 9:30-12:45)",
                fg="red",
            )
        )
    return value


def validate_month(ctx, param, value):
    if value is None:
        return value
    if not (1 <= value <= 12):
        raise click.BadParameter(
            click.style("❌ Month must be between 1 and 12.", fg="red")
        )
    return value
