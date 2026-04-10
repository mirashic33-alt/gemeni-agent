"""
startup.py — background initialization thread.

Sequence:
  1. Read keys from keystore
  2. Validate keys
  3. Create Gemini client
  4. Ping the model
  5. Load chat history and start chat session

Each step reports status to the UI via the `status` signal.
"""

from PySide6.QtCore import QThread, Signal

import data.keystore as keystore
from data.logger import get_logger
from llm.provider import GeminiProvider

log = get_logger("startup")


class StartupWorker(QThread):
    """
    Launched immediately after the main window is shown.
    Signals:
      status(str)  — status bar text
      done(object) — GeminiProvider ready to use
      failed(str)  — error message (provider not created)
    """

    status = Signal(str)
    done   = Signal(object)
    failed = Signal(str)

    def run(self) -> None:
        try:
            self._init()
        except Exception as exc:
            log.exception("Critical error during initialization")
            self.failed.emit(f"Error: {exc}")

    def _init(self) -> None:
        # Step 1 — read keys from encrypted keystore
        self.status.emit("Reading configuration...")

        # Step 2 — validate keys
        self.status.emit("Checking keys...")
        api_key = keystore.get("GEMINI_API_KEY")
        if not api_key:
            msg = "API key not set. Open settings (⚙)."
            log.warning(msg)
            self.failed.emit(msg)
            return
        log.info("API key loaded.")

        token = keystore.get("TELEGRAM_TOKEN")
        if not token:
            log.warning("TELEGRAM_TOKEN not set — Telegram channel unavailable.")

        chat_id = keystore.get("TELEGRAM_CHAT_ID")
        if not chat_id:
            log.warning("TELEGRAM_CHAT_ID not set.")

        # Step 3 — create client
        self.status.emit("Initializing Gemini...")
        provider = GeminiProvider(api_key)
        provider.connect()

        # Step 4 — test request
        self.status.emit("Testing model...")
        try:
            ok = provider.ping()
        except Exception as exc:
            log.error(f"Ping failed: {exc}")
            self.failed.emit(f"Model unavailable: {exc}")
            return

        if not ok:
            self.failed.emit("Model did not respond. Check your API key.")
            return

        # Step 5 — load history and create chat session
        self.status.emit("Loading chat history...")
        from data.chat_history import load
        history = load()
        log.info(f"Loaded {len(history)} messages from history.")
        system_prompt = (
            "Each user message contains the current date and time in brackets "
            "at the start (e.g. [10.04.2026, Friday, 15:14]). "
            "Use it silently for temporal orientation — to understand when messages "
            "were sent, what time of day it is, etc. "
            "Never repeat, quote, or draw attention to this timestamp unless the user "
            "explicitly asks what time or date it is."
        )
        provider.start_chat(history=history, system_prompt=system_prompt)

        # Done
        self.status.emit("Ready.")
        log.info("Initialization complete.")
        self.done.emit(provider)
