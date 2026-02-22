import os
import pathlib

from dotenv import load_dotenv

# Load config from ~/.mind-cli/.env (global install) with fallback to CWD/.env (development).
_ENV_PATH = pathlib.Path.home() / ".mind-cli" / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    load_dotenv()  # fallback: search CWD and parents (works for editable/dev installs)

# App Constants
PROJECT_KEY = os.getenv("PROJECT_KEY", "")
WORKING_HOURS_PER_DAY = 8
TIMEZONE = "Europe/Warsaw"
FAVORITES_PATH = pathlib.Path(str(pathlib.Path.home() / ".mind-cli" / "favorites.json"))
# Token cache path (no extension)
PLANNER_TOKEN_PATH = pathlib.Path(
    str(pathlib.Path.home() / ".mind-cli" / ".planner_token")
)

# Jira Configuration
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")


# Clockify Configuration
CLOCKIFY_BASE_API_URL = os.getenv(
    "CLOCKIFY_BASE_API_URL", "https://api.clockify.me/api/v1"
)
CLOCKIFY_API_KEY = os.getenv("CLOCKIFY_API_KEY", "")
CLOCKIFY_WORKSPACE_ID = os.getenv("CLOCKIFY_WORKSPACE_ID", "")
CLOCKIFY_PROJECT_ID = os.getenv("CLOCKIFY_PROJECT_ID", "")
CLOCKIFY_USER_ID = os.getenv("CLOCKIFY_USER_ID", "")
CLOCKIFY_REPORTS_API_URL = os.getenv(
    "CLOCKIFY_REPORTS_API_URL", "https://reports.api.clockify.me"
)
CLOCKIFY_REPORT_SAVE_PATH = os.getenv(
    "CLOCKIFY_REPORT_SAVE_PATH", str(pathlib.Path.home() / "Downloads")
)
CLOCKIFY_REPORT_BASE_NAME = os.getenv("CLOCKIFY_REPORT_BASE_NAME", "clockify_report")
TASK_PROVIDER = os.getenv("TASK_PROVIDER", "jira")


# Planner Configuration
PLANNER_BASE_URL = os.getenv("PLANNER_BASE_URL", "")
PLANNER_USERNAME = os.getenv("PLANNER_USERNAME", "")
PLANNER_PASSWORD = os.getenv("PLANNER_PASSWORD", "")
PLANNER_USER_ID = int(os.getenv("PLANNER_USER_ID", "0"))


_required_env_names = [
    "JIRA_BASE_URL",
    "JIRA_EMAIL",
    "JIRA_API_TOKEN",
    "CLOCKIFY_API_KEY",
    "CLOCKIFY_WORKSPACE_ID",
    "CLOCKIFY_PROJECT_ID",
    "CLOCKIFY_USER_ID",
    "PLANNER_BASE_URL",
    "PLANNER_USERNAME",
    "PLANNER_PASSWORD",
    "PLANNER_USER_ID",
]
_missing = [name for name in _required_env_names if not globals()[name]]
if _missing:
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    msg = f"{YELLOW}Missing required env: {', '.join(_missing)}. Set them in your .env file.{RESET}"
    raise SystemExit(msg)
