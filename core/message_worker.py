"""
message_worker.py — background thread for sending a message to Gemini.
Spawned for each user message. Uses agent_loop for tool-calling.
"""

from PySide6.QtCore import QThread, Signal

from core import agent_loop
from data.logger import get_logger
from tools.time_sense import get_datetime_context
from tools.file_tools import ALL_TOOLS
from tools.shell_tools import ALL_SHELL_TOOLS

log = get_logger("chat")


class MessageWorker(QThread):
    """
    Signals:
      response(str) — model response text
      error(str)    — error message
      interim(str)  — emitted mid-loop while tools are running
    """
    response = Signal(str)
    interim  = Signal(str)
    error    = Signal(str)

    def __init__(self, provider, message: str, bridge=None, parent=None):
        super().__init__(parent)
        self._provider = provider
        self._message  = message
        self._bridge   = bridge

    def run(self) -> None:
        try:
            from data.chat_history import load
            full_history = load()
            context_history = full_history[:-1]

            datetime_context = get_datetime_context()
            message_with_time = f"[{datetime_context}]\n{self._message}"

            text = agent_loop.run(
                client=self._provider.client,
                model=self._provider.model,
                system_prompt=self._provider.system_prompt,
                history=context_history,
                message=message_with_time,
                tools=ALL_TOOLS + ALL_SHELL_TOOLS,
                on_interim=self.interim.emit,
            )
            self.response.emit(text)

            if self._bridge:
                import data.keystore as keystore
                self._bridge.tick_diary(
                    api_key=keystore.get("GEMINI_API_KEY") or "",
                    model=self._provider.model,
                )

        except Exception as exc:
            log.error(f"Send error: {exc}")
            self.error.emit(str(exc))
