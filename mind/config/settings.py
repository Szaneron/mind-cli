import os

from dotenv import load_dotenv

load_dotenv()

# Jira Configuration
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "https://your-domain.atlassian.net")
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
    "CLOCKIFY_REPORTS_API_URL", "https://reports.api.clockify.me/v1"
)
CLOCKIFY_REPORT_SAVE_PATH = os.getenv("CLOCKIFY_REPORT_SAVE_PATH", "")
CLOCKIFY_REPORT_BASE_NAME = os.getenv("CLOCKIFY_REPORT_BASE_NAME", "clockify_report")
TASK_PROVIDER = os.getenv("TASK_PROVIDER", "jira")

# App Constants
WORKING_HOURS_PER_DAY = 8
TIMEZONE = "Europe/Warsaw"
