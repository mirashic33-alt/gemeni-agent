# Gemeni Agent

A personal AI assistant built with PySide6 + Google Gemini + Telegram.
Desktop chat app with a Telegram mirror — same agent, two interfaces.

## Features

- **Chat UI** — dark theme, markdown rendering, live thinking timer
- **Telegram bot** — full two-way mirror, all tools available
- **Tool-calling loop** — agent can use tools autonomously (no AFC)
- **Filesystem tools** — read, write, patch, move, search files
- **Shell tools** — run PowerShell commands and scripts
- **Memory system** — SOUL.md, USER.md, MEMORY.md, daily logs, personal diary
- **Skills** — drop a `.md` file into `workspace/skills/` to extend agent behavior
- **Internet search** — Google Search via Gemini grounding
- **Encrypted key storage** — Windows DPAPI, no `.env` file

## Stack

- Python 3.11+
- PySide6
- google-genai (Gemini API)
- python-telegram-bot

## Setup

1. Clone the repo
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run:
   ```
   pythonw main.pyw
   ```
4. Open **Settings → Keys** and enter your Gemini API key
5. Optionally add a Telegram bot token and chat ID

## Project structure

```
core/        agent loop, memory, background workers
llm/         Gemini client
tools/       filesystem and shell tools
channels/    Telegram bot
ui/          PySide6 interface
data/        config, chat history, key storage
workspace/   agent's working files (memory, skills, logs)
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) — stages 1–21 done, image support is next.
