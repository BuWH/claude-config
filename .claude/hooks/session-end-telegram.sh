#!/bin/bash
# SessionEnd hook: Send notification to Telegram when Claude Code exits

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

# Load .env and export variables
[ -f "$PROJECT_DIR/.env" ] && set -a && source "$PROJECT_DIR/.env" && set +a

# Activate virtualenv and run Python script
source "$PROJECT_DIR/.venv/bin/activate" && \
python3 "$PROJECT_DIR/.claude/hooks/session_end_notifier.py"
