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

# Other
TASK_PROVIDER=jira
```

### 3. Install as a package (available globally in any terminal)

```bash
# Standard install
pip install .
# Or editable install (code changes are applied immediately)
pip install -e .
```

After installation, the `mind` command will be available **in any terminal** (VS Code, RubyMine, PyCharm iTerm, Terminal.app, etc.) if Python is in your PATH.

## Usage

### Time logging

```bash
# Log time for PROJ-123 from 9:00 to 17:00 (today)
mind log PROJ-123 9-17

# Log time on a specific date
mind log PROJ-123 9:30-12:45 15.11
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

### Help

```bash
mind --help
mind log --help
mind show --help
```

## Requirements

- Python 3.10+
- macOS / Linux / Windows

## License

MIT
