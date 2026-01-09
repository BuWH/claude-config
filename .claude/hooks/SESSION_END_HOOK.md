# Session End Hook - Updated Implementation

## Overview

The session-end hook has been rewritten to use the Bun-based `claude-code-telegram-bot` CLI instead of the Python implementation.

## Changes

### Old Implementation (Python)
- Used Python with virtualenv
- Required separate Python package installation
- Used subprocess to call Python CLI module
- More dependencies and complexity

### New Implementation (Bun/TypeScript)
- Uses Bun runtime with TypeScript
- Directly calls Telegram API via fetch
- Single TypeScript file, no package dependencies needed
- Faster execution and simpler setup

## Files

### `/Users/wenhe/agent/.claude/hooks/session-end-telegram.sh`
Main hook script that:
1. Loads environment variables from both bot and project directories
2. Pipes session data from stdin to the TypeScript handler

### `/Users/wenhe/code/claude-code-telegram-bot/packages/cli/src/session-end-handler.ts`
TypeScript handler that:
1. Reads session data from stdin
2. Parses the transcript JSONL file
3. Extracts session statistics (tokens, duration, tool calls, etc.)
4. **Generates AI summary** using Azure OpenAI (if credentials available)
5. Formats a MarkdownV2 message
6. Sends directly to Telegram API

## Environment Variables

Required in `.env`:
- `TELEGRAM_BOT_TOKEN` - Your bot token
- `ALLOWED_USERS` - Comma-separated list of chat IDs (first one receives notifications)

Optional for AI Summary:
- `AZURE_AI_PROJECT_ENDPOINT` - Azure AI endpoint (e.g., `https://xxx.services.ai.azure.com/api/projects/xxx`)
- `AZURE_API_KEY` (or `AZURE_AI_API_KEY` or `AZURE_OPENAI_API_KEY`) - Azure API key
- `AZURE_AI_DEPLOYMENT` - Deployment name (defaults to `gpt-5-mini`)

Other Optional:
- `CLAUDE_TELEGRAM_BOT_DIR` - Path to bot directory (defaults to `/Users/wenhe/code/claude-code-telegram-bot`)
- `DEBUG` - Set to `1` or `true` to enable debug logging

## Testing

Test the handler manually:
```bash
echo '{"reason":"user_exit","transcript_path":"~/.nonexistent","cwd":"$(pwd)","session_id":"test-123"}' | \
  DEBUG=1 bun /Users/wenhe/code/claude-code-telegram-bot/packages/cli/src/session-end-handler.ts
```

## Features

The notification includes:
- 📁 Project directory and git branch
- 🤖 Model used
- ⏱️ Session duration
- 💬 Conversation turns
- 🔧 Tool call count
- 📊 Session token usage (prompt + completion)
- 🤖 **AI-generated summary** (bullet points of what was accomplished)
- 📊 **Summary token usage** (tracked separately for Azure API calls)

## Benefits

1. **No Python dependencies** - Uses Bun which is already installed
2. **Faster** - TypeScript with Bun is faster than Python
3. **Simpler** - Direct API calls, no package management
4. **Better typed** - Full TypeScript type safety
5. **Easier to maintain** - Single codebase with the bot
