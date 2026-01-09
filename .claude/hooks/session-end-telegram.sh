#!/bin/bash
# SessionEnd hook: Send notification to Telegram when Claude Code exits
# Uses the claude-code-telegram-bot Bun CLI

set -e

# Project directory (where the hook was invoked)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

# Path to the claude-code-telegram-bot CLI
BOT_CLI_DIR="${CLAUDE_TELEGRAM_BOT_DIR:-/Users/wenhe/code/claude-code-telegram-bot}"

# Load .env from bot directory for Telegram credentials
if [ -f "$BOT_CLI_DIR/.env" ]; then
    set -a
    source "$BOT_CLI_DIR/.env"
    set +a
fi

# Also load project .env if available (for Azure API keys, etc.)
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Read session data from stdin and process with Node.js
cat | bun "$BOT_CLI_DIR/packages/cli/src/session-end-handler.ts"
