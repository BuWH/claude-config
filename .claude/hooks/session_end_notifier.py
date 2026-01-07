#!/usr/bin/env python3
"""Send Claude Code session summary to Telegram.

This script reads session data from stdin (JSON format) and sends
a detailed summary including costs, tool calls, and LLM-generated summary
to Telegram via the claude-code-telegram-bot.
"""

import json
import sys
import os
import subprocess
from datetime import datetime

# Import markdown utilities from claude-code-telegram-bot package
try:
    from claude_code_telegram_bot.formatting.markdown import escape_markdown_v2
except ImportError:
    # Fallback if package is not installed
    def escape_markdown_v2(text: str) -> str:
        """Escape text for Telegram MarkdownV2 format."""
        if not text:
            return text
        special_chars = r'_*[]()~`>#+-=|{}.!'
        return ''.join(f'\\{c}' if c in special_chars else c for c in text)

# Optional httpx for REST API calls
try:
    import httpx
except ImportError:
    httpx = None


def _debug(msg: str) -> None:
    """Print debug message if DEBUG is set."""
    if os.environ.get("DEBUG"):
        print(f"[DEBUG] {msg}", file=sys.stderr)


def _get_field(entry: dict, field: str, default=None):
    """Get field from entry or nested message structure."""
    if field in entry:
        return entry[field]
    if "message" in entry:
        return entry["message"].get(field, default)
    return default


def parse_transcript(transcript_path: str) -> dict:
    """Parse the transcript JSONL file to extract session statistics."""
    transcript_path = os.path.expanduser(transcript_path)

    if not os.path.exists(transcript_path):
        _debug(f"Transcript file not found: {transcript_path}")
        return {
            "duration": None, "total_tokens": 0, "prompt_tokens": 0,
            "completion_tokens": 0, "model": "unknown", "tool_calls": [],
            "tool_call_count": 0, "errors": [], "conversation_turns": 0,
            "git_branch": None, "conversation": []
        }

    _debug(f"Parsing transcript: {transcript_path}")

    turns = []
    timestamps = []
    total_input_tokens = 0
    total_output_tokens = 0
    tool_calls = []
    models = set()
    git_branch = None

    try:
        with open(transcript_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    turns.append(entry)

                    if len(turns) == 1:
                        _debug(f"First entry keys: {list(entry.keys())}")

                    if "timestamp" in entry:
                        timestamps.append(entry["timestamp"])

                    if not git_branch:
                        git_branch = _get_field(entry, "gitBranch")

                    # Extract token usage
                    usage = _get_field(entry, "usage", {})
                    total_input_tokens += usage.get("input_tokens", 0)
                    total_output_tokens += usage.get("output_tokens", 0)

                    # Extract model
                    model = _get_field(entry, "model")
                    if model:
                        models.add(model)

                    # Extract tool calls
                    content = _get_field(entry, "content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_calls.append(block.get("name", "unknown"))

                except json.JSONDecodeError as e:
                    print(f"Error parsing JSONL line: {e}", file=sys.stderr)

    except Exception as e:
        print(f"Error reading transcript: {e}", file=sys.stderr)
        return {
            "duration": None, "total_tokens": 0, "prompt_tokens": 0,
            "completion_tokens": 0, "model": "unknown", "tool_calls": [],
            "tool_call_count": 0, "errors": [], "conversation_turns": 0,
            "git_branch": None, "conversation": []
        }

    # Calculate duration
    duration_seconds = None
    if timestamps:
        try:
            start = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
            end = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
            duration_seconds = int((end - start).total_seconds())
        except Exception as e:
            print(f"Error calculating duration: {e}", file=sys.stderr)

    # Count conversation turns
    conversation_turns = sum(1 for t in turns if t.get("type") == "user")

    # Extract conversation for AI summary
    conversation = []
    for turn in turns:
        msg = turn.get("message", turn) if "message" in turn else turn
        if not msg:
            continue

        role = msg.get("role", turn.get("type", "unknown"))
        content = turn.get("content", msg.get("content", ""))

        text_content = ""
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content += block.get("text", "")
        elif isinstance(content, str):
            text_content = content

        if text_content.strip():
            conversation.append({"role": role, "content": text_content[:1000]})

    result = {
        "duration": duration_seconds,
        "total_tokens": total_input_tokens + total_output_tokens,
        "prompt_tokens": total_input_tokens,
        "completion_tokens": total_output_tokens,
        "model": list(models)[0] if models else "unknown",
        "tool_calls": tool_calls,
        "tool_call_count": len(tool_calls),
        "errors": [],
        "conversation_turns": conversation_turns,
        "git_branch": git_branch,
        "conversation": conversation,
    }

    _debug(f"Parsed: duration={duration_seconds}s, tokens={result['total_tokens']}, "
           f"turns={conversation_turns}, tools={len(tool_calls)}")

    return result


def get_session_summary(data: dict) -> dict:
    """Extract relevant session information from the hook input data.

    The SessionEnd hook provides:
    - session_id
    - transcript_path (path to JSONL file with full conversation)
    - cwd (current working directory)
    - permission_mode
    - hook_event_name
    - reason (exit reason)
    """
    reason = data.get("reason", "unknown")
    transcript_path = data.get("transcript_path", "")
    project_dir = data.get("cwd", "")

    # Parse the transcript to get actual session statistics
    transcript_data = parse_transcript(transcript_path)

    summary = {
        "reason": reason,
        "project_dir": project_dir,
        "session_id": data.get("session_id", ""),
        **transcript_data,  # Merge transcript data
    }
    return summary


def format_duration(seconds: int | None) -> str:
    """Format duration in human-readable format."""
    if seconds is None:
        return "N/A"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def generate_ai_summary(conversation: list) -> tuple[str, dict]:
    """Generate an AI summary of the conversation using Azure OpenAI REST API.

    Returns:
        tuple: (summary_text, token_usage_dict) where token_usage_dict has
               keys: input_tokens, output_tokens, total_tokens
    """
    if not conversation or not httpx:
        return "", {}

    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    api_key = os.environ.get("AZURE_API_KEY") or os.environ.get("AZURE_AI_API_KEY") or os.environ.get("AZURE_OPENAI_API_KEY")
    deployment = os.environ.get("AZURE_AI_DEPLOYMENT", "gpt-5-mini")

    if not endpoint or not api_key:
        return "", {}

    try:
        conv_text = "\n".join(
            f"{t.get('role', 'unknown')}: {t.get('content', '')[:200]}"
            for t in conversation[-10:]
        )

        prompt = f"Summarize this Claude Code session in under 100 words. Use bullet points. Focus on what was accomplished.\n\nConversation:\n{conv_text}\n\nSummary:"

        # Build Azure OpenAI URL from Foundry endpoint
        if ".services.ai.azure.com" in endpoint:
            resource_name = endpoint.split(".services.ai.azure.com")[0].split("://")[-1]
            base_url = f"https://{resource_name}.openai.azure.com"
        else:
            base_url = endpoint.rstrip('/').replace('/api/projects/wenhe-project', '')

        url = f"{base_url}/openai/v1/chat/completions"

        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"messages": [{"role": "user", "content": prompt}], "model": deployment, "max_completion_tokens": 500},
            timeout=30.0
        )

        if response.status_code == 200:
            data = response.json()
            # Extract token usage
            usage = data.get("usage", {})
            token_info = {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
            _debug(f"Summary generation tokens: input={token_info['input_tokens']}, output={token_info['output_tokens']}, total={token_info['total_tokens']}")
            return data["choices"][0]["message"]["content"].strip(), token_info
        else:
            print(f"API error: {response.status_code} - {response.text}", file=sys.stderr)

    except Exception as e:
        print(f"Summary generation error: {e}", file=sys.stderr)

    return "", {}


def generate_session_stats(summary: dict, summary_tokens: dict = None) -> str:
    """Generate session stats with MarkdownV2 styling.

    Args:
        summary: Session summary dict
        summary_tokens: Optional dict with keys: input_tokens, output_tokens, total_tokens
    """
    lines = []

    # Project info - use full path with markdown
    if summary["project_dir"]:
        project = escape_markdown_v2(summary['project_dir'])
        lines.append(f"📁 *Project:* `{project}`")
        if summary["git_branch"]:
            branch = escape_markdown_v2(summary['git_branch'])
            lines.append(f"🌿 *Branch:* `{branch}`")

    # Session stats with emoji and markdown
    model = escape_markdown_v2(summary['model'])
    duration = escape_markdown_v2(format_duration(summary['duration']))
    lines.append(f"🤖 *Model:* `{model}`")
    lines.append(f"⏱️ *Duration:* {duration}")
    lines.append(f"💬 *Turns:* {summary['conversation_turns']}")
    lines.append(f"🔧 *Tool calls:* {summary['tool_call_count']}")

    # Session token usage with emoji and markdown
    if summary["total_tokens"]:
        lines.append(f"📊 *Tokens:* {summary['total_tokens']:,}")
        if summary["prompt_tokens"] and summary["completion_tokens"]:
            lines.append(f"   ├─ *Prompt:* {summary['prompt_tokens']:,}")
            lines.append(f"   └─ *Completion:* {summary['completion_tokens']:,}")

    # Summary generation tokens (separate section)
    if summary_tokens and summary_tokens.get("total_tokens", 0) > 0:
        lines.append(f"🤖 *Summary Token:* {summary_tokens['total_tokens']:,}")
        if summary_tokens.get("input_tokens") and summary_tokens.get("output_tokens"):
            lines.append(f"   ├─ *Input:* {summary_tokens['input_tokens']:,}")
            lines.append(f"   └─ *Output:* {summary_tokens['output_tokens']:,}")

    # Errors
    if summary["errors"]:
        error_count = len(summary["errors"])
        lines.append(f"⚠️ *Errors:* {error_count}")

    return "\n".join(lines)


def send_to_telegram(message: str) -> bool:
    """Send message to Telegram using claude-telegram-bot CLI."""
    try:
        # Get chat IDs from environment or config
        env = os.environ.copy()

        # Use the virtual environment Python from telegram-bot project
        # Default to /Users/wenhe/code/claude-code-telegram-bot/.venv/bin/python
        bot_python = os.environ.get(
            "CLAUDE_TELEGRAM_BOT_PYTHON",
            "/Users/wenhe/code/claude-code-telegram-bot/.venv/bin/python"
        )

        # Use python -m to run the CLI with MarkdownV2 formatting
        result = subprocess.run(
            [bot_python, "-m", "claude_code_telegram_bot.cli.main", "send", message, "--parse-mode", "MarkdownV2"],
            capture_output=True,
            text=True,
            env=env,
        )

        if result.returncode == 0:
            return True
        else:
            print(f"Error sending to Telegram: {result.stderr}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Failed to send Telegram message: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    # Read JSON from stdin
    try:
        data = json.load(sys.stdin)
        _debug(f"Received hook data: {json.dumps(data, indent=2)[:500]}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    summary = get_session_summary(data)
    _debug(f"Session summary: {json.dumps(summary, indent=2)[:800]}")

    ai_summary, summary_tokens = generate_ai_summary(summary.get("conversation", []))
    session_stats = generate_session_stats(summary, summary_tokens)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Note: = characters need to be escaped for MarkdownV2
    header = f"{escape_markdown_v2('='*16)}\n\n🔔 *CC Session Ended*\n\nReason: *{escape_markdown_v2(summary['reason'])}*\nTime: *{escape_markdown_v2(timestamp)}*"

    parts = [header, session_stats]
    if ai_summary:
        parts.append("📝 *Summary:*")
        # Format as bullet points and escape for MarkdownV2
        summary_lines = []
        for line in ai_summary.strip().split('\n'):
            line = line.strip()
            if line:
                if not line.startswith('•'):
                    line = f"• {line}"
                summary_lines.append(escape_markdown_v2(line))
        parts.append('\n'.join(summary_lines))

    full_message = "\n\n".join(parts)

    if os.environ.get("DEBUG"):
        print(f"\n{'='*60}\nMESSAGE:\n{'='*60}\n{full_message}\n{'='*60}\n", file=sys.stderr)

    if send_to_telegram(full_message):
        _debug("Sent to Telegram")
        sys.exit(0)
    else:
        print("Failed to send session summary", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
