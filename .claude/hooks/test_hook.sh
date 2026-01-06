#!/bin/bash
# Test script for session-end hook

# Get the most recent transcript
TRANSCRIPT_FILE=$(find ~/.claude/projects/-Users-wenhe-agent -name "*.jsonl" -type f 2>/dev/null | xargs ls -lt 2>/dev/null | head -1 | awk '{print $NF}')

echo "Testing with transcript: $TRANSCRIPT_FILE"

# Load .env and activate venv
[ -f .env ] && set -a && source .env && set +a
source .venv/bin/activate

# Create test input and pipe to Python
cat <<EOF | python3 .claude/hooks/session_end_notifier.py
{
  "session_id": "test-session-123",
  "transcript_path": "$TRANSCRIPT_FILE",
  "cwd": "/Users/wenhe/agent",
  "permission_mode": "default",
  "hook_event_name": "SessionEnd",
  "reason": "user_exit"
}
EOF
