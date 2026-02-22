# Mind CLI

✨ **Mind CLI** – CLI tool for time logging and reporting automation.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Szaneron/mind-cli.git
cd mind-cli
```

### 2. Configure environment variables

Copy `mind/config/.env_template` to `mind/config/.env` and fill in your credentials:

```env
# Jira Configuration
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your.email@example.com
JIRA_API_TOKEN=your_jira_api_token

# Clockify Configuration
CLOCKIFY_BASE_API_URL=https://api.clockify.me/api/v1
CLOCKIFY_API_KEY=your_clockify_api_key
CLOCKIFY_WORKSPACE_ID=your_workspace_id
CLOCKIFY_PROJECT_ID=your_project_id
CLOCKIFY_USER_ID=your_user_id
CLOCKIFY_REPORTS_API_URL=https://reports.api.clockify.me
CLOCKIFY_REPORT_SAVE_PATH=/Users/
CLOCKIFY_REPORT_BASE_NAME=your_report_name

# Planner Configuration
PLANNER_BASE_URL=https://your-planner-domain/api
PLANNER_USERNAME=your_planner_username
PLANNER_PASSWORD=your_planner_password
PLANNER_USER_ID=your_numeric_user_id

# Other
TASK_PROVIDER=jira
PROJECT_KEY=PROJ
```

### 3. Install as a package (available globally in any terminal)

```bash
# Standard install
pip install .
# Or editable install (code changes are applied immediately)
pip install -e .
```

After installation, the `mind` command will be available **in any terminal** (VS Code, RubyMine, PyCharm iTerm, Terminal.app, etc.) if Python is in your PATH.

## Quick Reference

```bash
# --- Time logging ---
mind log PROJ-123 9-17                  # Log time for issue, today
mind log PROJ-123 9:30-12:45 15.11      # Log time for issue, specific date
mind log 9-17                           # Log using issue key from Git branch
mind log PROJ-456 9-17                  # Log with explicit key override

# --- Display entries ---
mind show                               # Today's entries
mind show 15.11                         # Entries for a specific day (current year)
mind show 15.11.2025                    # Entries for a specific day with year

# --- Hours summary ---
mind hours                              # Current month summary
mind hours 11                           # Specific month summary

# --- Download reports ---
mind download report                    # PDF monthly report for current month
mind download report 1                  # PDF monthly report for specific month

# --- Tasks (Jira) ---
mind tasks                              # All open tasks (default project)
mind tasks --active                     # Only active tasks (In Progress, Code Review)
mind tasks --project PEG                # Tasks for specific project
mind tasks --project PEG --active       # Active tasks for specific project

# --- Favorites ---
mind fav add PEG-1234                   # Add issue to favorites
mind fav remove PEG-1234                # Remove issue from favorites
mind fav list                           # List all favorites
mind fav clear                          # Clear all favorites

# --- Planned availability (Planner) ---
mind plan show                          # Planned availability, current month
mind plan show 3                        # Planned availability, specific month
mind plan compare                       # Planned vs logged hours, current month
mind plan compare 11                    # Planned vs logged hours, specific month

# --- Help ---
mind --help
mind log --help
mind show --help
mind hours --help
mind download --help
mind download report --help
mind tasks --help
mind fav --help
mind plan --help
mind plan show --help
mind plan compare --help
```

## Usage

### Time logging

You can log time by providing an explicit Jira issue key, or let Mind CLI automatically detect the issue key from your current Git branch name (e.g. `PROJ-123-feature` → `PROJ-123`).

```bash
# Log time for PROJ-123 from 9:00 to 17:00 (today)
mind log PROJ-123 9-17

# Log time on a specific date
mind log PROJ-123 9:30-12:45 15.11

# Log time using issue key auto-detected from current Git branch (e.g. PEG-123-add-favorites)
mind log 9-17

# You can still override the detected key by providing one explicitly:
mind log PROJ-456 9-17
```

### Display entries

```bash
# Show entries from today
mind show

# Show entries from a specific day
mind show 15.11
```

### Hours summary

```bash
# Show hours for the current month
mind hours

# Show hours for a specific month
mind hours 11
```

### Download reports

```bash
# Download PDF report for the current month
mind download report

# Download PDF report for a specific month
mind download report 1
```

### Tasks listing (Jira)

```bash
# List open tasks assigned to you (default project from env)
mind tasks

# List only active tasks (In Progress, Code Review)
mind tasks --active

# List tasks for a specific project
mind tasks --project PEG

# List only active tasks for a specific project
mind tasks --project PEG --active
```

- By default, tasks are filtered by the project key from your `.env` (`PROJECT_KEY`).
- `--active` shows only tasks with status "In Progress" or "Code Review".
- Tasks are sorted by status: IN PROGRESS, ANALYSIS, CODE REVIEW, TO DO, ON STAGING, READY FOR PRODUCTION, READY FOR QA, QA FAILED, ON HOLD.

### Favorites

```bash
# Add a Jira issue to favorites
mind fav add PEG-1234

# Remove a Jira issue from favorites
mind fav remove PEG-1234

# List your favorite issues
mind fav list

# Clear all favorites
mind fav clear
```

- Favorites are stored locally in `~/.mind-cli/favorites.json`.
- You can quickly manage your favorite issues.

### Planned availability (Planner)

```bash
# Show planned availability for the current month (newest day first)
mind plan show

# Show planned availability for a specific month
mind plan show 3

# Compare planned vs logged hours per day for the current month
mind plan compare

# Compare for a specific month
mind plan compare 11
```

- `plan show` displays detailed time ranges and work mode per day, with total planned hours and monthly maximum at the bottom.
- `plan compare` shows planned vs Clockify logged hours side by side, with per-day difference (OK / Missing / overtime) and a total summary.
- Requires `PLANNER_BASE_URL`, `PLANNER_USERNAME`, `PLANNER_PASSWORD` and `PLANNER_USER_ID` in your `.env`.
- JWT token is cached in `~/.mind-cli/.planner_token` and refreshed automatically when expired.

### Help

Every command supports the `--help` flag for usage and options, e.g.:

```bash
mind --help
mind log --help
```

## Requirements

- Python 3.10+
- macOS / Linux / Windows

## License

MIT
