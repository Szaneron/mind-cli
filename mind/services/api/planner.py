"""
Planner API service.

Provides functions for communicating with the MindPal Planner API:
- Authentication (login to obtain JWT token, cached to disk)
- Fetching planned availabilities
"""

import pathlib
import stat

import httpx

from mind.config.settings import (
    PLANNER_BASE_URL,
    PLANNER_PASSWORD,
    PLANNER_TOKEN_PATH,
    PLANNER_USERNAME,
)


class PlannerAPI:
    """MindPal Planner API client.

    Loads a cached JWT token from disk on startup. Falls back to a fresh
    login when no cache exists or the token is rejected (401). The token
    is persisted after every successful login so subsequent calls skip the
    auth request entirely.
    """

    def __init__(self) -> None:
        self.base_url = PLANNER_BASE_URL
        self.client = httpx.Client(timeout=10)
        self._token: str | None = self._load_token()

    # ------------------------------------------------------------------
    # Token persistence
    # ------------------------------------------------------------------

    @staticmethod
    def _load_token() -> str | None:
        """Return the cached token string, or None if no cache exists."""
        if PLANNER_TOKEN_PATH.exists():
            return PLANNER_TOKEN_PATH.read_text().strip() or None
        return None

    @staticmethod
    def _save_token(token: str) -> None:
        """Persist token to disk with owner-read-only permissions (600)."""
        PLANNER_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        PLANNER_TOKEN_PATH.write_text(token)
        PLANNER_TOKEN_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)

    @staticmethod
    def _clear_token() -> None:
        """Remove stale token cache."""
        if PLANNER_TOKEN_PATH.exists():
            PLANNER_TOKEN_PATH.unlink()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    @property
    def _auth_headers(self) -> dict[str, str]:
        if not self._token:
            raise RuntimeError("Not authenticated — call login() first.")
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def login(self) -> None:
        """Authenticate, store the JWT token in memory and on disk."""
        if not PLANNER_USERNAME or not PLANNER_PASSWORD:
            raise RuntimeError(
                "PLANNER_USERNAME and PLANNER_PASSWORD must be set in your .env file."
            )
        url = f"{self.base_url}/auth/login/"
        payload = {"username": PLANNER_USERNAME, "password": PLANNER_PASSWORD}
        response = self.client.post(url, json=payload)
        response.raise_for_status()
        self._token = response.json()["token"]
        self._save_token(self._token)

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------

    def get_availabilities(self, start_date: str, end_date: str) -> list[dict]:
        """
        Fetch planned availabilities for the given date range.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date:   End date in YYYY-MM-DD format.

        Returns:
            List of availability dicts from the API.
        """
        if not self._token:
            self.login()
        url = f"{self.base_url}/planner/availabilities/"
        params = {"startDate": start_date, "endDate": end_date}
        try:
            response = self.client.get(url, headers=self._auth_headers, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Cached token expired — re-login, clear stale cache, retry
                self._clear_token()
                self.login()
                response = self.client.get(
                    url, headers=self._auth_headers, params=params
                )
                response.raise_for_status()
            else:
                raise
        return response.json()
