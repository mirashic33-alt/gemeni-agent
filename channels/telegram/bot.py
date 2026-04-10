"""
bot.py — Telegram bot for the agent.

Runs in a separate thread after the provider is initialized.
Accepts messages only from the authorized TELEGRAM_CHAT_ID.
Uses the same GeminiProvider as the UI.
"""

import asyncio
import threading
from datetime import datetime

from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from telegram.constants import ChatAction

from data.logger import get_logger
from tools.time_sense import get_datetime_context

log = get_logger("telegram")


class TelegramBot:
    def __init__(self, token: str, chat_id: int, provider, bridge):
        self._token    = token
        self._chat_id  = chat_id
        self._provider = provider
        self._bridge   = bridge
        self._app      = None
        self._loop     = None
        self._thread   = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="telegram-bot")
        self._thread.start()
        log.info("Telegram bot started.")

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._main())

    async def _main(self):
        self._loop = asyncio.get_running_loop()
        self._app  = Application.builder().token(self._token).build()
        self._app.add_handler(CommandHandler("start", self._cmd_start))
        self._app.add_handler(CommandHandler("clear", self._cmd_clear))
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
        )
        async with self._app:
            await self._app.start()
            await self._app.updater.start_polling(drop_pending_updates=True)
            log.info("Telegram polling started.")
            await asyncio.Event().wait()  # block until stopped

    # ------------------------------------------------------------------
    # Methods callable from the Qt thread (thread-safe)
    # ------------------------------------------------------------------
    def post_message(self, text: str):
        """Send text to Telegram from any thread."""
        if self._loop and self._app:
            asyncio.run_coroutine_threadsafe(
                self._app.bot.send_message(chat_id=self._chat_id, text=text),
                self._loop
            )

    def post_typing(self):
        """Show typing indicator in Telegram."""
        if self._loop and self._app:
            asyncio.run_coroutine_threadsafe(
                self._app.bot.send_chat_action(
                    chat_id=self._chat_id, action=ChatAction.TYPING
                ),
                self._loop
            )

    # ------------------------------------------------------------------
    # Authorization guard
    # ------------------------------------------------------------------
    def _is_setup_mode(self) -> bool:
        """Setup mode: chat_id not configured yet."""
        return self._chat_id == 0

    def _is_authorized(self, update: Update) -> bool:
        cid = update.effective_chat.id
        if cid != self._chat_id:
            log.warning(f"Rejected message from chat_id={cid}")
            return False
        return True

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    async def _cmd_start(self, update: Update, _context):
        if self._is_setup_mode():
            cid = update.effective_chat.id
            await update.message.reply_text(
                f"Your chat ID: {cid}\n\nPaste it into Settings in the app, then restart."
            )
            log.info(f"Setup mode: told chat_id={cid} to user")
            return
        if not self._is_authorized(update):
            return
        await update.message.reply_text(
            f"Gemeni Agent online.\nModel: {self._provider.model}"
        )

    async def _cmd_clear(self, update: Update, _context):
        if not self._is_authorized(update):
            return
        from data.chat_history import clear
        clear()
        self._provider.start_chat(history=[])
        self._bridge.history_changed.emit()
        await update.message.reply_text("Chat history cleared.")
        log.info("History cleared via Telegram /clear")

    # ------------------------------------------------------------------
    # Incoming message
    # ------------------------------------------------------------------
    async def _on_message(self, update: Update, context):
        if not self._is_authorized(update):
            return

        text = update.message.text.strip()
        if not text:
            return

        ts = datetime.now().strftime("%H:%M")
        log.info(f"← Telegram: {text[:80]}")

        # Show user message in UI
        self._bridge.tg_user_message.emit(ts, text)

        # Show typing indicator in Telegram
        await context.bot.send_chat_action(
            chat_id=self._chat_id, action=ChatAction.TYPING
        )

        # Call the model (without blocking asyncio)
        try:
            datetime_context = get_datetime_context()
            message_with_time = f"[{datetime_context}]\n{text}"
            response = await asyncio.to_thread(
                self._provider.send, message_with_time
            )
        except Exception as exc:
            log.error(f"Error processing Telegram message: {exc}")
            await update.message.reply_text(f"Error: {exc}")
            return

        ts_resp = datetime.now().strftime("%H:%M")
        log.info(f"→ Telegram response: {response[:80]}")

        # Send response to Telegram
        await update.message.reply_text(response)

        # Show response in UI
        self._bridge.tg_agent_message.emit(ts_resp, response)

        # Save to history
        from data.chat_history import append
        append("user", text)
        append("agent", response)
        self._bridge.history_changed.emit()
