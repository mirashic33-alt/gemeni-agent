import re
import time
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QFont

from .theme_config import (
    STATE, ICON_FONT, MID_BUTTON_ICONS, SEND_ICON, MIC_ICON, UI_TEXTS, build_qss
)
from .settings_dialog import SettingsDialog
from core.names import get_agent_name, get_user_name, refresh as refresh_names


def create_hline():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Plain)
    line.setFixedHeight(1)
    return line


def _md_to_html(text: str) -> str:
    """Converts a small subset of markdown to HTML for QLabel rendering."""
    # Escape HTML special chars
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Headers (### ## #)
    text = re.sub(r'^#{1,3}\s+(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    # Bold **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Italic *text*
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    # Links [title](url) — show only title, full url in href
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                  r'<a href="\2" style="color:#FFB347;text-decoration:underline;">\1</a>', text)
    # Bullet list items
    text = re.sub(r'^[-*]\s+(.+)$', r'&nbsp;&nbsp;• \1', text, flags=re.MULTILINE)
    # Newlines → <br>
    text = text.replace("\n", "<br>")
    return text


def make_bubble(prefix, text, is_user):
    frame = QFrame()
    frame.setObjectName("bubble_user" if is_user else "bubble_agent")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(10, 6, 10, 8)
    layout.setSpacing(2)
    prefix_lbl = QLabel(prefix)
    prefix_lbl.setObjectName("bubble_prefix")
    text_lbl = QLabel()
    text_lbl.setObjectName("bubble_text")
    text_lbl.setWordWrap(True)
    text_lbl.setTextFormat(Qt.RichText)
    text_lbl.setOpenExternalLinks(True)
    text_lbl.setText(_md_to_html(text) if not is_user else text.replace("\n", "<br>"))
    layout.addWidget(prefix_lbl)
    layout.addWidget(text_lbl)
    return frame


class ChatArea(QFrame):
    """Scrollable chat area that holds message bubbles."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chat_bubble")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("chat_scroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.content = QWidget()
        self.content.setObjectName("chat_content")
        self._inner = QVBoxLayout(self.content)
        self._inner.setContentsMargins(8, 8, 8, 8)
        self._inner.setSpacing(6)
        self._inner.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll)

        self._auto_scroll = False
        self.scroll.verticalScrollBar().rangeChanged.connect(self._on_range_changed)

    def _on_range_changed(self, _min, maximum):
        if self._auto_scroll:
            self.scroll.verticalScrollBar().setValue(maximum)
            self._auto_scroll = False

    def add_bubble(self, prefix, text, is_user):
        bubble = make_bubble(prefix, text, is_user)
        self._inner.addWidget(bubble)
        return bubble

    def scroll_to_bottom(self):
        self._auto_scroll = True
        self.content.updateGeometry()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(UI_TEXTS["window_title"])
        self.resize(STATE.get("window_width", 580), STATE.get("window_height", 700))
        self.setObjectName("preview_panel")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(5)

        self.header = QWidget()
        _header_layout = QHBoxLayout(self.header)
        _header_layout.setContentsMargins(0, 0, 0, 0)
        _header_layout.setSpacing(6)
        _header_layout.setAlignment(Qt.AlignCenter)
        self.header_icon_label = QLabel("")
        self.header_icon_label.setObjectName("header_icon_label")
        self.header_text_label = QLabel(STATE.get("header_text", "Header"))
        self.header_text_label.setObjectName("header_label")
        _header_layout.addWidget(self.header_icon_label)
        _header_layout.addWidget(self.header_text_label)
        self.line1 = create_hline()

        self.top_buttons = QWidget()
        top_layout = QHBoxLayout(self.top_buttons)
        top_layout.setContentsMargins(0, 5, 0, 5)
        for text in UI_TEXTS["top_buttons"]:
            top_layout.addWidget(QPushButton(text))
        self.line2 = create_hline()

        self.chat_area = ChatArea()
        self.line3 = create_hline()

        self.mid_buttons = QWidget()
        mid_layout = QHBoxLayout(self.mid_buttons)
        mid_layout.setContentsMargins(0, 5, 0, 5)
        mid_layout.setSpacing(8)
        mid_layout.setAlignment(Qt.AlignLeft)
        self.mid_btn_list = []
        for icon_code in MID_BUTTON_ICONS:
            btn = QPushButton(icon_code)
            btn.setFont(QFont(*ICON_FONT))
            mid_layout.addWidget(btn)
            self.mid_btn_list.append(btn)

        # Clear chat button (🗑 index 1 — \uE74D)
        self.mid_btn_list[1].clicked.connect(self._on_clear_chat)
        # Settings button (⚙ \uE713)
        self.mid_btn_list[-1].clicked.connect(self._open_settings)
        self.line4 = create_hline()

        self.input_container = QWidget()
        outer_layout = QHBoxLayout(self.input_container)
        outer_layout.setContentsMargins(0, 5, 0, 5)

        self.input_bubble = QFrame()
        self.input_bubble.setObjectName("input_bubble")
        bubble_layout = QHBoxLayout(self.input_bubble)
        bubble_layout.setContentsMargins(5, 5, 5, 5)
        bubble_layout.setSpacing(5)

        self.input_area = QTextEdit()
        self.input_area.setObjectName("inner_input")
        self.input_area.setPlaceholderText(UI_TEXTS["input_placeholder"])
        self.input_area.installEventFilter(self)  # Enter = send

        self.send_btn = QPushButton(SEND_ICON)
        self.send_btn.setFont(QFont(*ICON_FONT))
        self.send_btn.setObjectName("send_btn")
        self.send_btn.setFixedSize(35, 35)
        self.send_btn.clicked.connect(self._on_send)

        bubble_layout.addWidget(self.input_area)
        bubble_layout.addWidget(self.send_btn, 0, Qt.AlignVCenter)

        self.mic_btn = QPushButton(MIC_ICON)
        self.mic_btn.setFont(QFont(*ICON_FONT))
        self.mic_btn.setObjectName("mic_btn")
        self.mic_btn.setFixedSize(45, 45)

        outer_layout.addWidget(self.input_bubble, 1)
        outer_layout.addWidget(self.mic_btn, 0, Qt.AlignVCenter)
        self.line5 = create_hline()

        # Status bar: left — progress/events, right — system stats
        self.status_bar = QFrame()
        self.status_bar.setObjectName("status_bar_frame")
        _status_layout = QHBoxLayout(self.status_bar)
        _status_layout.setContentsMargins(6, 2, 6, 2)
        _status_layout.setSpacing(0)

        self._status_left = QLabel(UI_TEXTS["status"])
        self._status_left.setObjectName("status_label")
        self._status_left.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._status_right = QLabel("")
        self._status_right.setObjectName("status_label_right")
        self._status_right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        _status_layout.addWidget(self._status_left, 1)
        _status_layout.addWidget(self._status_right, 0)

        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.line1)
        self.main_layout.addWidget(self.top_buttons)
        self.main_layout.addWidget(self.line2)
        self.main_layout.addWidget(self.chat_area, 1)
        self.main_layout.addWidget(self.line3)
        self.main_layout.addWidget(self.mid_buttons)
        self.main_layout.addWidget(self.line4)
        self.main_layout.addWidget(self.input_container)
        self.main_layout.addWidget(self.line5)
        self.main_layout.addWidget(self.status_bar)

        self.apply_state(STATE)
        self.setStyleSheet(build_qss(STATE))

        self._provider = None
        self._model_name = ""
        self._start_time = 0.0
        self._bridge = None   # set from main.py
        self._tg_bot = None   # set from main.py after bot starts

        # Request timer — ticks while the model is thinking (50 ms)
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

        # System monitor timer (2 sec)
        self._sys_timer = QTimer(self)
        self._sys_timer.setInterval(2000)
        self._sys_timer.timeout.connect(self._update_sys_stats)
        self._sys_timer.start()

    def apply_state(self, state):
        self.header.setVisible(state["show_header"])
        self.header.setMinimumHeight(state["header_height"])
        self.top_buttons.setVisible(state["show_top_btns"])
        self.chat_area.setVisible(state["show_chat"])
        self.mid_buttons.setVisible(state["show_mid_btns"])
        self.input_container.setVisible(state["show_input"])
        self.input_area.setMaximumHeight(state["input_height"])
        self.input_bubble.setMaximumHeight(state["input_height"] + 10)
        self.status_bar.setVisible(state.get("show_status", True))

        self.line1.setVisible(state.get("show_line1", True))
        self.line2.setVisible(state.get("show_line2", True))
        self.line3.setVisible(state.get("show_line3", True))
        self.line4.setVisible(state.get("show_line4", True))
        self.line5.setVisible(state.get("show_line5", True))

        mid_w = state.get("mid_btn_width", 52)
        for btn in self.mid_btn_list:
            btn.setFixedWidth(mid_w)

        hfont = state.get("header_font", "Arial")
        hsize = state.get("header_font_size", 14)
        hcolor = state.get("header_color", state["text_color"])
        self.header_text_label.setText(state.get("header_text", "Header"))
        self.header_text_label.setStyleSheet(
            f"color: {hcolor}; font-family: '{hfont}'; font-size: {hsize}px;"
        )
        icon_char = state.get("header_icon", "")
        icon_size = state.get("header_icon_size", 18)
        self.header_icon_label.setText(icon_char)
        self.header_icon_label.setStyleSheet(
            f"color: {hcolor}; font-family: 'Segoe UI'; font-size: {icon_size}px;"
        )
        self.header_icon_label.setVisible(bool(icon_char))

    def _open_settings(self):
        dialog = SettingsDialog(parent=self)
        dialog.exec()

    # ------------------------------------------------------------------
    # Chat history
    # ------------------------------------------------------------------
    def _load_history(self):
        """Loads history from file and renders it in the chat."""
        from data.chat_history import load, _limit as _history_limit
        messages = load()
        for msg in messages:
            prefix = f"[{msg.get('ts', '')}] {get_user_name() if msg['role'] == 'user' else get_agent_name()}"
            self.chat_area.add_bubble(prefix, msg["text"], is_user=(msg["role"] == "user"))
        self.chat_area.scroll_to_bottom()
        self._update_header_count()

    def _update_header_count(self):
        """Updates the message counter in the header."""
        from data.chat_history import load, _limit as _history_limit
        count = len(load())
        if self._model_name:
            self.set_header(f"{get_agent_name()}  ·  {self._model_name}  {count}/{_history_limit()}")

    def _on_clear_chat(self):
        from PySide6.QtWidgets import QMessageBox
        from data.chat_history import clear
        reply = QMessageBox.question(
            self, "Clear Chat",
            "Delete all chat history?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            clear()
            if self._provider:
                self._provider.start_chat(history=[], system_prompt=self._provider.system_prompt)
            # Clear chat widgets
            layout = self.chat_area._inner
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.set_status("Chat cleared.")
            self._update_header_count()

    # ------------------------------------------------------------------
    # Enter in input = send (Shift+Enter = new line)
    # ------------------------------------------------------------------
    def eventFilter(self, obj, event):
        if obj is self.input_area and event.type() == QEvent.KeyPress:
            key = event.key()
            mods = event.modifiers()
            if key in (Qt.Key_Return, Qt.Key_Enter) and not (mods & Qt.ShiftModifier):
                self._on_send()
                return True  # event consumed
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Sending a message
    # ------------------------------------------------------------------
    def _update_sys_stats(self):
        """Updates the right status panel with system stats."""
        from tools.system_monitor import get_system_stats
        self.set_status_right(get_system_stats())

    def _tick(self):
        """Updates the left status with a live timer."""
        elapsed = time.perf_counter() - self._start_time
        sec = int(elapsed)
        hs = int((elapsed - sec) * 100)
        self.set_status(f"Thinking...  {sec}.{hs:02d}s")

    def _on_send(self):
        from core.message_worker import MessageWorker

        text = self.input_area.toPlainText().strip()
        if not text:
            return
        if not self._provider:
            self.set_status("⚠  Model not ready.")
            return

        from data.chat_history import append
        from core.daily_log import append_message as log_msg
        ts = datetime.now().strftime("%H:%M")
        self.chat_area.add_bubble(f"[{ts}] {get_user_name()}", text, is_user=True)
        self.input_area.clear()
        self.chat_area.scroll_to_bottom()
        append("user", text)
        log_msg("user", text)
        self._update_header_count()

        self.send_btn.setEnabled(False)
        self.set_status("Thinking...")
        self._start_time = time.perf_counter()
        self._timer.start()

        # Show typing indicator in Telegram while model is thinking
        if self._tg_bot:
            self._tg_bot.post_typing()

        self._worker = MessageWorker(self._provider, text, bridge=self._bridge, parent=self)
        self._worker.response.connect(self._on_response)
        self._worker.interim.connect(self._on_interim)
        self._worker.error.connect(self._on_message_error)
        self._worker.start()

    def _on_interim(self, text: str):
        if text.startswith("[tool]"):
            self.set_status(text[6:])  # status bar only — no bubble, no Telegram
            return

        from core.daily_log import append_message as log_msg
        ts = datetime.now().strftime("%H:%M")
        self.chat_area.add_bubble(f"[{ts}] {get_agent_name()} ·", text, is_user=False)
        self.chat_area.scroll_to_bottom()
        log_msg("agent", text)
        if self._tg_bot:
            self._tg_bot.post_message(text)

    def _on_response(self, text: str):
        from data.chat_history import append
        from core.daily_log import append_message as log_msg
        self._timer.stop()
        elapsed = time.perf_counter() - self._start_time
        sec = int(elapsed)
        hs = int((elapsed - sec) * 100)

        ts = datetime.now().strftime("%H:%M")
        refresh_names()
        self.chat_area.add_bubble(f"[{ts}] {get_agent_name()}", text, is_user=False)
        self.chat_area.scroll_to_bottom()
        append("agent", text)
        log_msg("agent", text)
        self._update_header_count()
        self.send_btn.setEnabled(True)
        self.set_status(f"Done  ·  {sec}.{hs:02d}s")
        self._update_sys_stats()

        # Mirror response to Telegram
        if self._tg_bot:
            self._tg_bot.post_message(text)

    def _on_message_error(self, error: str):
        self._timer.stop()
        self.set_status(f"⚠  {error}")
        self._update_sys_stats()
        self.send_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------
    def set_status(self, text: str) -> None:
        """Left status bar — progress and events."""
        self._status_left.setText(text)

    def set_status_right(self, text: str) -> None:
        """Right status bar — system stats."""
        self._status_right.setText(text)

    def set_header(self, text: str) -> None:
        """Updates the window header text."""
        self.header_text_label.setText(text)

    def on_startup_done(self, provider) -> None:
        """Called when background initialization completes successfully."""
        self._provider = provider
        self._model_name = provider.model
        refresh_names()
        self.set_status(f"Ready  ·  {self._model_name}")
        self._load_history()

    def on_startup_failed(self, message: str) -> None:
        """Called on initialization error."""
        self._provider = None
        self.set_status(f"⚠  {message}")

    # ------------------------------------------------------------------
    # Incoming messages from Telegram → display in UI
    # ------------------------------------------------------------------
    def on_tg_interim(self, text: str):
        """Interim from Telegram-initiated agent call — show in UI only, no re-send."""
        if text.startswith("[tool]"):
            self.set_status(text[6:])  # status bar only
            return
        ts = datetime.now().strftime("%H:%M")
        self.chat_area.add_bubble(f"[{ts}] {get_agent_name()} ·", text, is_user=False)
        self.chat_area.scroll_to_bottom()

    def on_tg_user_message(self, ts: str, text: str):
        self.chat_area.add_bubble(f"[{ts}] {get_user_name()} (TG)", text, is_user=True)
        self.chat_area.scroll_to_bottom()
        self.set_status("Thinking...")
        self._start_time = time.perf_counter()
        self._timer.start()

    def on_tg_agent_message(self, ts: str, text: str):
        self._timer.stop()
        elapsed = time.perf_counter() - self._start_time
        sec = int(elapsed)
        hs = int((elapsed - sec) * 100)
        refresh_names()
        self.chat_area.add_bubble(f"[{ts}] {get_agent_name()} (TG)", text, is_user=False)
        self.chat_area.scroll_to_bottom()
        self._update_header_count()
        self.set_status(f"Done  ·  {sec}.{hs:02d}s")

    def on_tg_history_changed(self):
        self._update_header_count()
