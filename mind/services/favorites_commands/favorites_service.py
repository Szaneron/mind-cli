import json
from datetime import date

import httpx
from rich.console import Console

from mind.config.settings import FAVORITES_PATH
from mind.services.api import JiraAPI


class FavoritesService:
    """
    Service for managing favorite tasks persisted locally in mind/data/favorites.json.

    Each favorite is stored as: {"key": "PROJ-123", "summary": "...", "added_at": "YYYY-MM-DD"}
    """

    def __init__(self) -> None:
        self.console = Console()
        self.jira = JiraAPI()

    # --- Storage helpers ---

    def _handle_corrupted_file(self, message: str) -> list[dict]:
        import click

        self.console.print(message)
        if click.confirm("Do you want to clear the file and start fresh?"):
            FAVORITES_PATH.write_text("[]", encoding="utf-8")
            self.console.print(
                "🧹 [green]File favorites.json has been cleared.[/green]"
            )
            return []
        else:
            self.console.print(
                "❌ [red]Aborted. Please fix or remove favorites.json manually.[/red]"
            )
            raise SystemExit(1)

    def _load(self) -> list[dict]:
        """Load favorites list from disk. If file is invalid, ask user if it should be cleared."""
        if not FAVORITES_PATH.exists():
            return []
        try:
            data = json.loads(FAVORITES_PATH.read_text(encoding="utf-8"))
            if not isinstance(data, list) or not all(
                isinstance(f, dict) and "key" in f for f in data
            ):
                return self._handle_corrupted_file(
                    "[yellow]⚠️  File favorites.json has unexpected format.[/yellow]"
                )
            return data
        except (json.JSONDecodeError, OSError):
            return self._handle_corrupted_file(
                "[yellow]⚠️  Could not read favorites.json.[/yellow]"
            )

    def _save(self, favorites: list[dict]) -> bool:
        """Persist favorites list to disk. Returns False and prints error on failure."""
        try:
            FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)
            FAVORITES_PATH.write_text(
                json.dumps(favorites, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            return True
        except OSError as e:
            self.console.print(f"[red]❌ Could not save favorites: {e}[/red]")
            return False

    # --- Public commands ---

    def add(self, key: str) -> None:
        """Fetch task from Jira and add it to favorites. Prints result to console."""
        try:
            summary = self.jira.get_issue_summary(key)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self.console.print(f"[red]❌ Task {key} not found in Jira.[/red]")
            else:
                self.console.print(f"[red]❌ Jira error: {e}[/red]")
            return
        except Exception as e:
            self.console.print(f"[red]❌ Could not fetch task from Jira: {e}[/red]")
            return

        favorites = self._load()
        if any(f["key"] == key for f in favorites):
            self.console.print(f"[yellow]⚠️  {key} is already in favorites.[/yellow]")
            return

        favorites.append(
            {"key": key, "summary": summary, "added_at": date.today().isoformat()}
        )
        if self._save(favorites):
            self.console.print(f"⭐ [green]{key} {summary}[/green] added to favorites.")

    def remove(self, key: str) -> None:
        """Remove a task from favorites. Prints result to console."""
        favorites = self._load()
        removed_entry = next((f for f in favorites if f["key"] == key), None)
        filtered = [f for f in favorites if f["key"] != key]
        if removed_entry is None:
            self.console.print(f"[yellow]⚠️  {key} is not in favorites.[/yellow]")
            return
        if self._save(filtered):
            summary = removed_entry.get("summary", "")
            self.console.print(
                f"🗑️  [green]{key} {summary}[/green] removed from favorites."
            )

    def list_all(self) -> None:
        """Print all favorite tasks to console."""
        favorites = self._load()
        if not favorites:
            self.console.print(
                "[yellow]No favorite tasks yet. Use 'mind fav add PROJ-123' to add one.[/yellow]"
            )
            return
        self.console.print(f"⭐ [bold]Favorite tasks ({len(favorites)}):[/bold]")
        for entry in favorites:
            summary = entry.get("summary", "")
            self.console.print(
                f"  [blue]{entry['key']}[/blue] {summary}  [dim]added {entry['added_at']}[/dim]"
            )

    def clear(self) -> bool:
        """Clear all favorite tasks. Returns True if cleared, False if already empty or save failed."""
        if self.is_empty():
            return False
        return self._save([])

    def is_empty(self) -> bool:
        """Return True if favorites list is empty."""
        return not self._load()
