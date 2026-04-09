"""
bridge.py — thread-safe bridge between the Telegram bot and the UI.

PySide6 Signals can be emitted from any thread — Qt automatically
queues the call to the main thread (QueuedConnection).
"""

from PySide6.QtCore import QObject, Signal


class AgentBridge(QObject):
    # Telegram → UI: incoming user message and model response
    tg_user_message  = Signal(str, str)   # ts, text
    tg_agent_message = Signal(str, str)   # ts, text

    # Notify UI to refresh message counter in the header
    history_changed  = Signal()
