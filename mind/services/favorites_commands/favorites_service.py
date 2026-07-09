import json
import re
from datetime import date

import httpx
from rich.console import Console

from mind.config.settings import FAVORITES_PATH, TASK_PROVIDER

_ISSUE_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")


class FavoritesService:
    """
    Service for managing favorite tasks persisted locally in ~/.mind-cli/favorites.json.

    Favorites are stored as a map keyed by the favorite key/alias:
        {
          "PEG-1234": {"type": "jira", "key": "PEG-1234", "description": "...", "provider": "jira"},
          "ds":       {"type": "text", "description": "Daily Standup", "provider": "trello"}
        }

    The old list format is migrated automatically on load.
    """

    def __init__(self) -> None:
        self.console = Console()

    # --- Storage helpers ---

    def _handle_corrupted_file(self, message: str) -> dict:
        import click

        self.console.print(message)
        if click.confirm("Do you want to clear the file and start fresh?"):
            FAVORITES_PATH.write_text("{}", encoding="utf-8")
            self.console.print(
                "🧹 [green]File favorites.json has been cleared.[/green]"
            )
            return {}
        else:
            self.console.print(
                "❌ [red]Aborted. Please fix or remove favorites.json manually.[/red]"
            )
            raise SystemExit(1)

    def _load(self) -> dict:
        """Load favorites map from disk, migrating the legacy list format if needed."""
        if not FAVORITES_PATH.exists():
            return {}
        try:
            data = json.loads(FAVORITES_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return self._handle_corrupted_file(
                "[yellow]⚠️  Could not read favorites.json.[/yellow]"
            )

        if isinstance(data, list):
            migrated = self._migrate_from_list(data)
            self._save(migrated)
            return migrated
        if isinstance(data, dict) and all(isinstance(v, dict) for v in data.values()):
            return data
        return self._handle_corrupted_file(
            "[yellow]⚠️  File favorites.json has unexpected format.[/yellow]"
        )

    def _migrate_from_list(self, data: list) -> dict:
        """Convert the legacy list format into the keyed-map format."""
        migrated: dict = {}
        for item in data:
            if not isinstance(item, dict) or "key" not in item:
                continue
            key = item["key"]
            migrated[key] = {
                "type": item.get("type", "jira"),
                "key": key,
                "description": item.get("description", item.get("summary", "")),
                "provider": item.get("provider", "jira"),
                "added_at": item.get("added_at", date.today().isoformat()),
            }
        return migrated

    def _save(self, favorites: dict) -> bool:
        """Persist favorites map to disk. Returns False and prints error on failure."""
        try:
            FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)
            FAVORITES_PATH.write_text(
                json.dumps(favorites, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            return True
        except OSError as e:
            self.console.print(f"[red]❌ Could not save favorites: {e}[/red]")
            return False

    @staticmethod
    def _entry_type(entry: dict) -> str:
        return entry.get("type", "jira")

    @staticmethod
    def _entry_provider(entry: dict) -> str:
        return entry.get("provider", "jira")

    def _find_existing_key(self, favorites: dict, identifier: str) -> str | None:
        """Return the stored key matching identifier (case-insensitive), or None."""
        target = identifier.strip().lower()
        for key in favorites:
            if key.lower() == target:
                return key
        return None

    # --- Public API ---

    def find(self, identifier: str) -> dict | None:
        """Look up a favorite by key/alias (case-insensitive), independent of provider."""
        favorites = self._load()
        existing = self._find_existing_key(favorites, identifier)
        if existing is None:
            return None
        entry = favorites[existing]
        return {**entry, "key": entry.get("key", existing)}

    @staticmethod
    def favorite_to_task_entry(favorite: dict):
        """Convert a stored favorite into a TaskEntry ready for logging."""
        from mind.services.providers.base import TaskEntry

        description = favorite.get("description", favorite.get("summary", ""))
        key = favorite.get("key", "")
        if favorite.get("type", "jira") == "jira" and key:
            return TaskEntry(
                task_name=key, description=f"[{key}] {description}", labels=[]
            )
        return TaskEntry(task_name=description, description=description, labels=[], use_clockify_task=False)

    def add(
        self,
        identifier: str,
        text: str | None = None,
        default_time: str | None = None,
    ) -> None:
        """
        Add a favorite, or update default_time/text on an existing one.

        - Two arguments (alias + text) → a plain text favorite, no API calls.
        - One argument → resolved through the active provider (Jira fetches the summary).
        - If the identifier is already a favorite, updates its text/default_time in place
          instead of hitting the provider again.
        """
        favorites = self._load()
        existing_key = self._find_existing_key(favorites, identifier)
        if existing_key is not None:
            self._update_existing(favorites, existing_key, text, default_time)
            return

        if text is not None:
            self._add_text(identifier, text, provider=TASK_PROVIDER, default_time=default_time)
            return

        from mind.services.providers import get_task_provider

        provider = get_task_provider()
        if provider.name == "jira":
            self._add_jira(identifier, provider, default_time=default_time)
        else:
            summary = provider.get_summary(identifier)
            self._add_text(identifier, summary, provider=provider.name, default_time=default_time)

    def _update_existing(
        self,
        favorites: dict,
        key: str,
        text: str | None,
        default_time: str | None,
    ) -> None:
        """Update description and/or default_time on an already-stored favorite."""
        entry = favorites[key]
        changed = []
        if text is not None:
            entry["description"] = text
            changed.append("text")
        if default_time is not None:
            entry["default_time"] = default_time
            changed.append("default time")

        if not changed:
            self.console.print(f"[yellow]⚠️  {key} is already in favorites.[/yellow]")
            return
        if self._save(favorites):
            self.console.print(
                f"✏️  [green]{key}[/green] updated ({', '.join(changed)})."
            )

    def _add_text(
        self, alias: str, text: str, provider: str, default_time: str | None = None
    ) -> None:
        key = alias.strip()
        if not key:
            self.console.print("[red]❌ Alias cannot be empty.[/red]")
            return
        favorites = self._load()
        entry = {
            "type": "text",
            "description": text,
            "provider": provider,
            "added_at": date.today().isoformat(),
        }
        if default_time is not None:
            entry["default_time"] = default_time
        favorites[key] = entry
        if self._save(favorites):
            self.console.print(f"⭐ [green]{key} → {text}[/green] added to favorites.")

    def _add_jira(self, identifier: str, provider, default_time: str | None = None) -> None:
        key = identifier.strip().upper()
        if not _ISSUE_KEY_PATTERN.match(key):
            self.console.print(
                "[red]❌ Issue key must be in format PROJ-123, "
                'or add a text favorite: fav add <alias> "<text>".[/red]'
            )
            return
        try:
            summary = provider.get_summary(key)
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
        entry = {
            "type": "jira",
            "key": key,
            "description": summary,
            "provider": "jira",
            "added_at": date.today().isoformat(),
        }
        if default_time is not None:
            entry["default_time"] = default_time
        favorites[key] = entry
        if self._save(favorites):
            self.console.print(f"⭐ [green]{key} {summary}[/green] added to favorites.")

    def remove(self, key: str) -> None:
        """Remove a favorite by key/alias. Prints result to console."""
        favorites = self._load()
        existing = self._find_existing_key(favorites, key)
        if existing is None:
            self.console.print(f"[yellow]⚠️  {key} is not in favorites.[/yellow]")
            return
        entry = favorites.pop(existing)
        if self._save(favorites):
            description = entry.get("description", entry.get("summary", ""))
            self.console.print(
                f"🗑️  [green]{existing} {description}[/green] removed from favorites."
            )

    def list_all(self, show_all: bool = False) -> None:
        """Print favorites to console. By default only the active provider's favorites."""
        favorites = self._load()
        items = list(favorites.items())
        hidden_count = 0
        if not show_all:
            visible = [
                (key, entry)
                for key, entry in items
                if self._entry_provider(entry) == TASK_PROVIDER
            ]
            hidden_count = len(items) - len(visible)
            items = visible

        if not items:
            if hidden_count:
                self.console.print(
                    f"[yellow]No favorites for provider '{TASK_PROVIDER}'. "
                    f"Use 'mind fav list --all' to see all {hidden_count}.[/yellow]"
                )
            else:
                self.console.print(
                    "[yellow]No favorite tasks yet. Use 'mind fav add PROJ-123' "
                    'or \'mind fav add ds "Daily Standup"\' to add one.[/yellow]'
                )
            return

        scope = "all providers" if show_all else f"provider '{TASK_PROVIDER}'"
        self.console.print(f"⭐ [bold]Favorite tasks ({len(items)}, {scope}):[/bold]")
        for key, entry in items:
            description = entry.get("description", entry.get("summary", ""))
            provider_label = self._entry_provider(entry)
            type_label = self._entry_type(entry)
            default_time = entry.get("default_time")
            time_label = f", ⏱ {default_time}" if default_time else ""
            self.console.print(
                f"  [blue]{key}[/blue] {description}  "
                f"[dim]({type_label}, {provider_label}{time_label})[/dim]"
            )

    def clear(self) -> bool:
        """Clear all favorites. Returns True if cleared, False if already empty or save failed."""
        if self.is_empty():
            return False
        return self._save({})

    def is_empty(self) -> bool:
        """Return True if there are no favorites."""
        return not self._load()
