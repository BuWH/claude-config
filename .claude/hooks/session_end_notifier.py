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

# Try to import httpx for REST API calls
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


def get_session_summary(data: dict) -> dict:
    """Extract relevant session information from the JSON data."""
    summary = {
        "reason": data.get("reason", "unknown"),
        "duration": data.get("duration_seconds"),
        "total_tokens": data.get("total_tokens"),
        "prompt_tokens": data.get("prompt_tokens"),
        "completion_tokens": data.get("completion_tokens"),
        "model": data.get("model"),
        "tool_calls": data.get("tool_calls", []),
        "tool_call_count": len(data.get("tool_calls", [])),
        "errors": data.get("errors", []),
        "conversation_turns": data.get("conversation_turns", 0),
        "project_dir": data.get("project_dir"),
        "git_branch": data.get("git_branch"),
        "conversation": data.get("conversation", []),
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


def generate_ai_summary(conversation: list) -> str:
    """Generate an AI summary of the conversation using Azure OpenAI REST API."""
    if not HAS_HTTPX:
        return ""

    if not conversation:
        return ""

    # Get Azure OpenAI settings from environment
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    api_key = os.environ.get("AZURE_API_KEY") or os.environ.get("AZURE_AI_API_KEY") or os.environ.get("AZURE_OPENAI_API_KEY")
    deployment = os.environ.get("AZURE_AI_DEPLOYMENT", "gpt-5-mini")

    if not endpoint or not api_key:
        return ""

    try:
        # Build a simplified conversation summary
        conv_text = []
        for turn in conversation[-10:]:  # Last 10 turns to save tokens
            role = turn.get("role", "unknown")
            content = turn.get("content", "")[:200]  # Truncate long messages
            conv_text.append(f"{role}: {content}")

        conversation_str = "\n".join(conv_text)

        prompt = f"""Summarize this Claude Code session in under 200 words. Focus on what was accomplished.

Conversation:
{conversation_str}

Summary:"""

        # Build the REST API URL for Azure AI Foundry
        # URL format: https://<resource>.openai.azure.com/openai/v1/chat/completions
        # Extract resource name from endpoint
        # endpoint format: https://wenheopenai.services.ai.azure.com/api/projects/wenhe-project
        # Convert to: https://wenheopenai.openai.azure.com/openai/v1/chat/completions
        if ".services.ai.azure.com" in endpoint:
            resource_name = endpoint.split(".services.ai.azure.com")[0].split("://")[-1]
            base_url = f"https://{resource_name}.openai.azure.com"
        else:
            base_url = endpoint.rstrip('/').replace('/api/projects/wenhe-project', '')

        url = f"{base_url}/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        body = {
            "messages": [{"role": "user", "content": prompt}],
            "model": deployment,
            "max_completion_tokens": 2000  # Higher for reasoning models
        }

        response = httpx.post(url, headers=headers, json=body, timeout=30.0)

        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        else:
            print(f"API error: {response.status_code} - {response.text}", file=sys.stderr)
            return ""

    except Exception as e:
        print(f"Summary generation error: {e}", file=sys.stderr)
        return ""


def format_ai_summary_as_bullets(summary_text: str) -> str:
    """Format AI summary as bullet points with styling."""
    if not summary_text:
        return ""

    # Split by sentences and format as bullets
    sentences = [s.strip() for s in summary_text.split('.') if s.strip()]
    bullets = ["- " + s + "." for s in sentences if s]
    return "\n".join(bullets)


def generate_session_stats(summary: dict) -> str:
    """Generate session stats with styling."""
    lines = []

    # Project info - use full path
    if summary["project_dir"]:
        lines.append(f"📁 Project: {summary['project_dir']}")
        if summary["git_branch"]:
            lines.append(f"🌿 Branch: {summary['git_branch']}")

    # Session stats with emoji
    lines.append(f"⏱️ Duration: {format_duration(summary['duration'])}")
    lines.append(f"💬 Turns: {summary['conversation_turns']}")
    lines.append(f"🔧 Tool calls: {summary['tool_call_count']}")

    # Token usage with emoji
    if summary["total_tokens"]:
        lines.append(f"📊 Tokens: {summary['total_tokens']:,}")
        if summary["prompt_tokens"] and summary["completion_tokens"]:
            lines.append(f"   ├─ Prompt: {summary['prompt_tokens']:,}")
            lines.append(f"   └─ Completion: {summary['completion_tokens']:,}")

    # Errors
    if summary["errors"]:
        error_count = len(summary["errors"])
        lines.append(f"⚠️ Errors: {error_count}")

    return "\n".join(lines)


def send_to_telegram(message: str) -> bool:
    """Send message to Telegram using claude-telegram-bot CLI."""
    try:
        # Get chat IDs from environment or config
        env = os.environ.copy()

        # Use the claude-telegram-bot CLI
        result = subprocess.run(
            ["claude-telegram-bot", "send", message],
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
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract session information
    summary = get_session_summary(data)

    # Generate the AI summary (optional)
    ai_summary = generate_ai_summary(summary.get("conversation", []))

    # Generate the session stats
    session_stats = generate_session_stats(summary)

    # Build the full message - summary at the end
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"🔔 Claude Code Session Ended\n"
    header += f"Reason: {summary['reason']} | Time: {timestamp}"

    parts = [header, session_stats]

    if ai_summary:
        parts.append("\n📝 Summary:")
        parts.append(format_ai_summary_as_bullets(ai_summary))

    full_message = "\n\n".join(parts)

    # Send to Telegram
    success = send_to_telegram(full_message)

    if success:
        print("Session summary sent to Telegram", file=sys.stderr)
        sys.exit(0)
    else:
        print("Failed to send session summary", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
