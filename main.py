import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.theme_config import STATE, build_qss
from core.startup import StartupWorker
from data.logger import setup_logger, get_logger
import data.keystore as keystore

log = get_logger("main")


def main():
    setup_logger()

    # Load encrypted keys on startup (if the file exists)
    keystore.load_if_exists()

    app = QApplication(sys.argv)
    app.setStyleSheet(build_qss(STATE))

    window = MainWindow()
    window.show()

    from core.bridge import AgentBridge
    bridge = AgentBridge(parent=app)
    bridge.tg_user_message.connect(window.on_tg_user_message)
    bridge.tg_agent_message.connect(window.on_tg_agent_message)
    bridge.history_changed.connect(window.on_tg_history_changed)

    def _start_telegram(provider):
        token   = keystore.get("TELEGRAM_TOKEN")
        chat_id = keystore.get("TELEGRAM_CHAT_ID")
        if not token:
            log.warning("Telegram not started: token not set.")
            return
        try:
            from channels.telegram.bot import TelegramBot
            bot = TelegramBot(
                token=token, chat_id=int(chat_id) if chat_id else 0,
                provider=provider, bridge=bridge
            )
            bot.start()
            window._tg_bot = bot
            if not chat_id:
                log.info("Telegram started in setup mode (chat_id not set).")
        except Exception as exc:
            log.error(f"Failed to start Telegram bot: {exc}")

    worker = StartupWorker(parent=app)
    worker.status.connect(window.set_status)
    worker.done.connect(window.on_startup_done)
    worker.done.connect(_start_telegram)
    worker.failed.connect(window.on_startup_failed)
    worker.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
