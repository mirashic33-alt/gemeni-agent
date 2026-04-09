# Gemeni Agent — Development Plan

> One stage — one checkpoint. Don't move forward until the current step works.

---

## Project structure

```
gemeni-agent/
│
├── main.py                        entry point
├── PLAN_EN.md
├── README.md
├── requirements.txt
├── .gitignore
│
├── core/
│   ├── startup.py                 background initialization (QThread)
│   ├── message_worker.py          background message dispatch (QThread)
│   └── bridge.py                  thread-safe bridge: Qt ↔ asyncio (Telegram)
│
├── llm/
│   └── provider.py                Gemini client (google-genai)
│
├── tools/
│   ├── time_sense.py              date/time context for the prompt
│   └── system_monitor.py          CPU, RAM, disk (psutil)
│
├── channels/
│   └── telegram/
│       └── bot.py                 Telegram bot (python-telegram-bot v20+)
│
├── ui/
│   ├── main_window.py             main window
│   ├── settings_dialog.py         settings dialog (keys → keystore)
│   └── theme_config.py            dark theme (QSS)
│
├── data/
│   ├── logger.py                  logger with rotation (300 lines)
│   ├── chat_history.py            chat history (JSON, 100 messages)
│   └── keystore.py                encrypted key storage via Windows DPAPI
│
└── workspace/                     agent's working files
    ├── agent.md                   system prompt / manifest (filled over time)
    └── diary/                     daily notes written by the agent
```

---

## Stages

### ✅ Stage 1 — Project skeleton
- [ ] Create all folders
- [ ] Move `ui_export.pyw` → `ui/main_window.py`, rename class to `MainWindow`
- [ ] Move `theme_config.py` → `ui/theme_config.py`
- [ ] Create empty `__init__.py` in every package
- [ ] Create `main.py` as the single entry point
- **Checkpoint:** `python main.py` → window opens

---

### ✅ Stage 2 — Settings dialog and theme
- [ ] `ui/settings_dialog.py` — three fields: Gemini API Key, Telegram Bot Token, Telegram Chat ID
- [ ] Mask API Key and Token fields (`EchoMode.Password`)
- [ ] Apply theme globally via `QApplication.setStyleSheet()`
- **Checkpoint:** settings dialog opens in dark theme

---

### ✅ Stage 3 — Encrypted key storage
- [ ] `data/keystore.py` — Windows DPAPI encryption via `ctypes` (no extra libraries)
- [ ] Keys stored in `data/keys.enc`, not in a plain-text `.env`
- [ ] `keystore.load_if_exists()` called at startup — transparent, no password
- **Checkpoint:** keys survive restart without a `.env` file

---

### ✅ Stage 4 — Gemini provider and background initialization
- [ ] `llm/provider.py` — Gemini client (`google-genai`, model `gemini-3-flash-preview`)
- [ ] `data/logger.py` — trimmed to 300 lines, session separator on each start
- [ ] `core/startup.py` — `StartupWorker(QThread)`: read keys → ping model → load history
- [ ] Status bar updates on every step
- [ ] After load: header shows `Gemeni · <model>`, status shows `Ready · <model>`
- **Checkpoint:** status bar completes all steps, model name appears in header

---

### ✅ Stage 5 — Chat and session memory
- [ ] `core/message_worker.py` — `MessageWorker(QThread)` for background requests
- [ ] `Enter` = send, `Shift+Enter` = new line (via `eventFilter`)
- [ ] `client.chats.create(history=...)` — model remembers the full session
- [ ] `data/chat_history.py` — JSON in `workspace/chat_history.json`, limit 100 messages
- [ ] Clear button 🗑 — clears history and resets the chat session
- **Checkpoint:** model remembers previous messages after restart

---

### ✅ Stage 6 — Status bar and system monitor
- [ ] Left side: progress → `Thinking... 3.45s` (live timer at 50 ms) → `Done · 3.21s`
- [ ] Right side: `CPU: 23% | RAM: 64% | C: 93.1GB` (psutil, every 2 sec)
- [ ] Timer uses left side, monitor uses right side — they never conflict
- **Checkpoint:** timer ticks in real time, system stats update independently

---

### ✅ Stage 7 — Telegram bot
- [ ] `channels/telegram/bot.py` — polling in a separate thread (asyncio)
- [ ] `core/bridge.py` — `AgentBridge(QObject)` with Qt signals for thread-safe exchange
- [ ] Two-way sync: message sent in UI appears in Telegram, and vice versa
- [ ] Typing indicator while the model is thinking
- [ ] Commands: `/start`, `/clear`
- **Checkpoint:** messages sync in both directions

---

### ⬜ Stage 8 — System prompt from file
- [ ] Read `workspace/agent.md` at each startup
- [ ] Pass it to `provider.start_chat(system_prompt=...)`
- [ ] The model can append to the file on its own over time
- **Checkpoint:** editing `agent.md` changes the model's behavior

---

### ⬜ Stage 9 — Filesystem tools
- [ ] `tools/filesystem.py` — `list_dir`, `read_file`, `write_file` scoped to `workspace/`
- [ ] Connect to Gemini via function calling
- **Checkpoint:** ask the agent to list files in workspace — it does

---

### ⬜ Stage 10 — System tray
- [ ] `ui/tray.py` — Windows system tray icon
- [ ] Closing the window hides it instead of killing the process
- [ ] Tray menu: Show, Exit
- **Checkpoint:** minimize → find in tray → restore

---

## Current status

**Done:** Stages 1–7  
**Next:** Stage 8 — system prompt from `workspace/agent.md`
