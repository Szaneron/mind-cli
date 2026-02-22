import click

from mind import __app_name__, __version__
from mind.commands import download, favorites, planner, statistics, tasks, time


@click.group()
@click.version_option(version=__version__, prog_name=__app_name__)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    ✨ MIND CLI ✨ - Work automation

    Tool for logging time in Clockify, fetching reports, and more.
    """
    ctx.ensure_object(dict)


# Register commands from modules
cli.add_command(time.log)
cli.add_command(time.show)
cli.add_command(time.hours)
cli.add_command(download.download)
cli.add_command(favorites.fav)
cli.add_command(tasks.tasks)
cli.add_command(planner.plan)
cli.add_command(statistics.stats)


if __name__ == "__main__":
    cli()
