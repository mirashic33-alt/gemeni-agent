"""
bot.py — Telegram bot for the agent.

Runs in a separate thread after the provider is initialized.
Accepts messages only from the authorized TELEGRAM_CHAT_ID.
Uses the same GeminiProvider as the UI.
"""

import asyncio
import re
import threading
from datetime import datetime

from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from telegram.constants import ChatAction

from core import agent_loop
from core.daily_log import append_message as log_msg
from data.logger import get_logger
from tools.file_tools import ALL_TOOLS
from tools.shell_tools import ALL_SHELL_TOOLS
from tools.time_sense import get_datetime_context

log = get_logger("telegram")


def _md_to_tg(text: str) -> str:
    """Convert markdown to Telegram HTML (parse_mode='HTML')."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'^#{1,3}\s+(.+)', r'<b>\1</b>', text, flags=re.MULTILINE)
    return text


class TelegramBot:
    def __init__(self, token: str, chat_id: int, provider, bridge):
        self._token       = token
        self._chat_id     = chat_id
        self._provider    = provider
        self._bridge      = bridge
        self._app    = None
        self._loop   = None
        self._thread = None

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
    _TG_LIMIT = 4000  # Telegram max is 4096, keep margin

    def _split(self, text: str) -> list[str]:
        """Split text into Telegram-sized chunks, breaking on newlines where possible."""
        if len(text) <= self._TG_LIMIT:
            return [text]
        chunks = []
        while text:
            if len(text) <= self._TG_LIMIT:
                chunks.append(text)
                break
            cut = text.rfind("\n", 0, self._TG_LIMIT)
            if cut == -1:
                cut = self._TG_LIMIT
            chunks.append(text[:cut])
            text = text[cut:].lstrip("\n")
        return chunks

    def post_message(self, text: str):
        """Send text to Telegram from any thread, splitting if needed."""
        if text.startswith("[tool]"):
            return  # tool status notifications are desktop status-bar only
        if self._loop and self._app:
            for chunk in self._split(text):
                asyncio.run_coroutine_threadsafe(
                    self._app.bot.send_message(
                        chat_id=self._chat_id,
                        text=_md_to_tg(chunk),
                        parse_mode="HTML",
                    ),
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
        self._provider.start_chat(history=[], system_prompt=self._provider.system_prompt)
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

        # Save user message to history and daily log before calling agent
        from data.chat_history import load, append
        context_history = load()
        append("user", text)
        log_msg("user", text)

        # Call agent_loop in a thread (has tools + internet, same as UI)
        try:
            datetime_context = get_datetime_context()
            message_with_time = f"[{datetime_context}]\n{text}"

            def _on_interim(text: str):
                self.post_message(text)             # [tool] skipped inside post_message
                self._bridge.tg_interim.emit(text)  # mirror to desktop UI

            def _run():
                return agent_loop.run(
                    client=self._provider.client,
                    model=self._provider.model,
                    system_prompt=self._provider.system_prompt,
                    history=context_history,
                    message=message_with_time,
                    tools=ALL_TOOLS + ALL_SHELL_TOOLS,
                    on_interim=_on_interim,
                )

            # Keep sending typing indicator every 4s while model works (plain thread)
            stop_typing = threading.Event()

            def _typing_thread():
                while not stop_typing.wait(timeout=4):
                    asyncio.run_coroutine_threadsafe(
                        context.bot.send_chat_action(
                            chat_id=self._chat_id, action=ChatAction.TYPING
                        ),
                        self._loop,
                    )

            t = threading.Thread(target=_typing_thread, daemon=True)
            t.start()
            try:
                response = await asyncio.to_thread(_run)
            finally:
                stop_typing.set()
        except Exception as exc:
            log.error(f"Error processing Telegram message: {exc}")
            await update.message.reply_text(f"Error: {exc}")
            return

        ts_resp = datetime.now().strftime("%H:%M")
        log.info(f"→ Telegram response: {response[:80]}")

        # Send response to Telegram — hard cap to avoid flooding on emoji loops
        _TG_MAX_RESPONSE = 3 * self._TG_LIMIT  # max 3 messages (~12 000 chars)
        tg_text = response if len(response) <= _TG_MAX_RESPONSE else (
            response[:_TG_MAX_RESPONSE] + "\n\n...[response too long, see desktop app]"
        )
        for chunk in self._split(tg_text):
            await update.message.reply_text(_md_to_tg(chunk), parse_mode="HTML")
        self._bridge.tg_agent_message.emit(ts_resp, response)

        # Save agent response
        append("agent", response)
        log_msg("agent", response)
        self._bridge.history_changed.emit()

        # Diary trigger via shared global counter
        import data.keystore as keystore
        self._bridge.tick_diary(
            api_key=keystore.get("GEMINI_API_KEY") or "",
            model=self._provider.model,
        )
