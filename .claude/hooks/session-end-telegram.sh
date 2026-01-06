#!/bin/bash
# SessionEnd hook: Send notification to Telegram when Claude Code exits

# Set project directory - use CLAUDE_PROJECT_DIR if set, otherwise use script directory
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

# Activate virtualenv
source "$PROJECT_DIR/.venv/bin/activate"

# Read JSON input from stdin and pipe to Python script
python3 "$PROJECT_DIR/.claude/hooks/session_end_notifier.py"

# Exit with success
exit 0
