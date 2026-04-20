"""
bridge.py — thread-safe bridge between the Telegram bot and the UI.

PySide6 Signals can be emitted from any thread — Qt automatically
queues the call to the main thread (QueuedConnection).
"""

import threading

from PySide6.QtCore import QObject, Signal


class AgentBridge(QObject):
    # Telegram → UI: incoming user message, interim text, and model response
    tg_user_message  = Signal(str, str)   # ts, text
    tg_interim       = Signal(str)        # text (no ts — shown like desktop interim)
    tg_agent_message = Signal(str, str)   # ts, text

    # Notify UI to refresh message counter in the header
    history_changed  = Signal()

    # Global diary counter shared across all channels
    _diary_lock    = threading.Lock()
    _diary_counter = 0

    def tick_diary(self, api_key: str, model: str) -> None:
        """Increment global message counter and trigger diary if threshold reached."""
        import data.config as config
        with self._diary_lock:
            self._diary_counter += 2
            if self._diary_counter >= config.get_diary_interval():
                self._diary_counter = 0
                do_trigger = True
            else:
                do_trigger = False
        if do_trigger and api_key:
            from core.diary_worker import trigger
            trigger(api_key=api_key, model=model)
