# Gemeni Agent — Development Roadmap

> One stage — one checkpoint. Don't move forward until the current step works.

---

## Project structure

```
gemeni-agent/
│
├── main.pyw                       entry point (no console window)
├── PLAN.md                        Russian development plan
├── ROADMAP.md                     this file
├── requirements.txt
├── .gitignore
│
├── core/
│   ├── startup.py                 background initialization (QThread)
│   ├── message_worker.py          background message dispatch (QThread)
│   ├── agent_loop.py              manual tool-calling loop
│   ├── bridge.py                  thread-safe bridge Qt ↔ Telegram + shared diary counter
│   ├── memory_loader.py           assembles system prompt from workspace files
│   ├── names.py                   reads agent/user names from SOUL.md / USER.md
│   ├── daily_log.py               appends every message to workspace/memory/YYYY-MM-DD.md
│   └── diary_worker.py            background diary writer (triggered every N messages)
│
├── llm/
│   └── provider.py                Gemini client (google-genai)
│
├── tools/
│   ├── file_tools.py              10 filesystem tools (list, read, write, patch, delete…)
│   ├── shell_tools.py             4 shell tools (run_shell, run_file, list/kill process)
│   ├── time_sense.py              date/time context injection
│   └── system_monitor.py          CPU, RAM, disk (psutil)
│
├── channels/
│   └── telegram/
│       └── bot.py                 Telegram bot — full agent_loop, typing indicator, HTML
│
├── ui/
│   ├── main_window.py             main window, chat bubbles, markdown rendering
│   ├── settings_dialog.py         4-tab settings dialog (Keys, Model, Agent, Channels)
│   └── theme_config.py            dark theme (QSS)
│
├── data/
│   ├── logger.py                  logger with 300-line rotation
│   ├── chat_history.py            chat history (JSON, configurable limit, 15K char cap)
│   ├── config.py                  typed getters/setters for all settings
│   ├── config.json                persistent settings file (editable by agent too)
│   └── keystore.py                encrypted key storage via Windows DPAPI
│
└── workspace/                     agent's working files
    ├── agent.md                   agent rules, tools, behavior guidelines
    ├── SOUL.md                    agent personality and name (written by agent)
    ├── USER.md                    facts about the user (written by agent)
    ├── MEMORY.md                  long-term facts (agent appends as needed)
    ├── chat_history.json          persistent chat history
    ├── skills/                    agent skill files (*.md, auto-loaded at startup)
    └── memory/
        ├── DIARY.md               agent's personal diary
        └── YYYY-MM-DD.md          daily conversation logs (auto-written)
```

---

## ✅ Completed stages

### Stage 1 — Project skeleton
Folders, imports, `main.pyw` entry point, window opens.

### Stage 2 — Settings dialog and dark theme
4-tab settings dialog (Keys, Model, Agent, Channels). Global QSS theme.
Keys tab: live (reads/writes keystore). Model and Agent tabs: live (reads/writes config.json).

### Stage 3 — Encrypted key storage
Windows DPAPI via `ctypes`. Keys in `data/keys.enc`. No `.env` file.

### Stage 4 — Gemini provider and background init
`StartupWorker(QThread)`: read keys → validate → create client → ping → load history → done.
Status bar updates at every step.

### Stage 5 — Chat and session memory
`MessageWorker(QThread)`. Enter = send, Shift+Enter = newline.
Chat history in `workspace/chat_history.json`. Clear button resets session without losing system prompt.

### Stage 6 — Status bar and system monitor
Left: live timer `Thinking... 3.45s` → `Done · 3.21s` (50 ms QTimer).
Right: `CPU: 23% | RAM: 64% | C: 93.1GB` (psutil, every 2 sec).

### Stage 7 — Telegram bot
Polling in a separate thread. `AgentBridge(QObject)` with Qt signals for thread-safe sync.
Two-way mirroring. `/start`, `/clear` commands. Typing indicator.

### Stage 8 — Settings expanded + config.json
`data/config.py` with typed getters/setters. `data/config.json` — human-readable, agent-editable.
All model and agent parameters configurable from UI without code changes.

### Stage 9 — Tool-calling infrastructure
`core/agent_loop.py` — manual loop (AFC disabled):
- Loop detector (same call N times → stop)
- Anti-hallucination wrapper on tool errors
- Retry nudge (model gave up after error → up to 2 pushes)
- Tool-first nudge (model replied with text instead of acting → up to 7 pushes)
- Result truncation (configurable char limit, default 12 000)
- MAX_TOKENS continuation only if response is meaningful (> 30% real letters)
- Narration rule: model writes brief commentary before/after every tool call

### Stage 10 — Filesystem tools (10 tools)
`list_files`, `read_file`, `write_file`, `append_file`, `patch_file`, `create_dir`,
`delete_file` (recycle bin via send2trash), `rename_file`, `move_file`, `search_files`.
Path aliases: `workspace:`, `desktop:`, `documents:`, `downloads:`, `home:`.

### Stage 11 — Shell tools (4 tools)
`run_shell` (PowerShell, stdout/stderr/exit code, up to 300s timeout),
`run_file` (.py/.bat/.exe/.ps1 as background process),
`list_processes`, `kill_process`.
Dangerous command blacklist: format, shutdown, rm -rf, reg delete, etc.

### Stage 12 — Agent memory files
`workspace/agent.md` — rules, tool reference, behavior guidelines.
`workspace/SOUL.md` — agent fills its own name and personality.
`workspace/USER.md` — agent fills user facts during conversation.
`workspace/MEMORY.md` — long-term facts, agent appends as needed.
`core/memory_loader.py` — assembles full system prompt at startup.

### Stage 13 — Skills system
`workspace/skills/` — any `.md` file is auto-loaded into the system prompt.
Agent can create new skills via `write_file`. Loaded at every startup.

### Stage 14 — Daily logs and dynamic names
`core/daily_log.py` — every message appended to `workspace/memory/YYYY-MM-DD.md` in real time.
`core/names.py` — reads agent/user names from SOUL.md / USER.md, refreshed after each response.
Dynamic names in all chat bubbles and Telegram messages.

### Stage 15 — Internet search
Google Search via Gemini grounding. Two separate `Tool` objects (required — mixing breaks search).
`include_server_side_tool_invocations=True` required or API returns 400.
Sources extracted from `grounding_metadata` and appended as clickable links.
Modes: `auto` / `never`. 🌐 indicator shown at any round where search occurs.

### Stage 16 — Markdown rendering
UI: `_md_to_html()` — converts markdown to Qt RichText (bold, italic, headers, clickable links).
Telegram: `_md_to_tg()` — converts to Telegram HTML (parse_mode="HTML").
Link URLs hidden behind anchor text. Link color: #FFB347 (amber, readable on dark background).

### Stage 17 — Interim messages and tool notifications
`on_interim` callback streams model narration and tool status to UI and Telegram in real time.
Tool calls emit `[tool]🔧 label` — shown in status bar only (not as chat bubbles, not in Telegram).
Non-tool interim text shown as `·` bubbles in chat and forwarded to Telegram.
Interim messages NOT saved to chat history (prevents consecutive-role history corruption).

### Stage 18 — Telegram full agent_loop integration
Telegram `_on_message` uses `agent_loop.run()` via `asyncio.to_thread`.
All 14 tools + internet available from Telegram, identical to desktop UI.
Typing indicator: daemon thread sends `ChatAction.TYPING` every 4 seconds via `run_coroutine_threadsafe`.
Long responses capped at 3 messages (~12 000 chars), remainder flagged as truncated.

### Stage 19 — Diary worker
`core/diary_worker.py` — background daemon thread, triggered every N messages.
Reads last 200 lines of memory logs. Separate API call (same model).
Model decides: something worth noting → writes to `DIARY.md`, nothing → returns `null`.
Shared global counter in `AgentBridge` (thread-safe, counts across all channels).

### Stage 20 — Workspace tree in system prompt
`_workspace_tree()` in `memory_loader.py` — walks `workspace/` at startup, builds ASCII tree.
Injected as `WORKSPACE STRUCTURE` block in system prompt.
Agent knows all file paths immediately without calling `list_files` first.

### Stage 21 — Bug fixes (April 2026)
- **Consecutive agent roles in history** → Gemini API hang. Fixed: interim no longer saved to history; agent_loop merges consecutive same-role entries before API call.
- **277K emoji message in history** → 230+ second hangs. Fixed: removed offending entry; chat_history now caps messages at 15 000 chars.
- **`start_chat` resetting system prompt on clear** → agent lost personality. Fixed: always pass `system_prompt=self._provider.system_prompt`.
- **Hardcoded "Ада" in daily_log** → wrong name if agent is renamed. Fixed: uses `get_agent_name()`.
- **Internet indicator only at round 0** → missed web searches in later rounds. Fixed: removed round restriction.
- **`max_result_chars` = 50 000** → leftover from debugging, caused context bloat. Fixed: 12 000.
- **Shared diary counter** → desktop and Telegram counted separately. Fixed: global counter in `AgentBridge` with `threading.Lock`.

---

## ⬜ Upcoming stages

### Stage 22 — Image support
- `analyze_image`: description, OCR, Q&A from image
- Upload via UI and Telegram
- Store in `workspace/images/`
- `generate_image`: generate images via Gemini

### Stage 23 — Digests and reflection
- Auto-generate daily digest
- `workspace/digests/` archive
- Extract facts from conversations → update `USER.md` / `MEMORY.md`
- Silent compaction: before history trim, agent saves what matters to `MEMORY.md`

### Stage 24 — Autonomous mode
- Scheduled tasks: digest, planner, ping, custom — on a timer
- Watchdog `.bat` script to auto-restart on crash
- Timer control from UI (enable/disable, mode, interval)

### Stage 25 — Token monitoring
- SQLite: every request logged (prompt/completion tokens, response time)
- Statistics window: per session and per day
- Breakdown: system prompt / history / current message

### Stage 26 — Polish and release
- Voice input
- Final security review
- Documentation and README

---

## Current status

**Done:** Stages 1–21
**Next:** Stage 22 — Image support
