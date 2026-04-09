"""
message_worker.py — background thread for sending a message to Gemini.
Spawned for each user message.
"""

from PySide6.QtCore import QThread, Signal

from data.logger import get_logger
from tools.time_sense import get_datetime_context

log = get_logger("chat")


class MessageWorker(QThread):
    """
    Signals:
      response(str) — model response text
      error(str)    — error message
    """
    response = Signal(str)
    error    = Signal(str)

    def __init__(self, provider, message: str, parent=None):
        super().__init__(parent)
        self._provider = provider
        self._message  = message

    def run(self) -> None:
        try:
            system_prompt = get_datetime_context()
            text = self._provider.send(self._message, system_prompt=system_prompt)
            self.response.emit(text)
        except Exception as exc:
            log.error(f"Send error: {exc}")
            self.error.emit(str(exc))
