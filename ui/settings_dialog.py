import data.keystore as keystore
import data.config as config
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QWidget,
    QScrollArea, QStackedWidget, QComboBox,
)
from PySide6.QtCore import Qt


_GEMINI_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-pro-preview",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]

_KEY_FIELDS = [
    ("GEMINI_API_KEY",   "Gemini API Key",     "Paste your Google AI Studio key...", True),
    ("TELEGRAM_TOKEN",   "Telegram Bot Token", "Paste token from @BotFather...",     True),
    ("TELEGRAM_CHAT_ID", "Telegram Chat ID",   "Your numeric chat_id...",            False),
]


def _hline(layout: QVBoxLayout):
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Plain)
    line.setFixedHeight(1)
    layout.addWidget(line)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 460)
        self.resize(600, 460)
        self.setModal(True)

        self._save_actions: list = []
        self._tab_btns: dict[str, QPushButton] = {}
        self._tab_order: list[str] = []
        self._stack = QStackedWidget()

        self._build_ui()

    # ── Save ─────────────────────────────────────────────────────────────────

    def _on_save(self):
        for action in self._save_actions:
            try:
                action()
            except Exception:
                pass
        self.accept()

    # ── UI skeleton ───────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        title_bar = QWidget()
        title_bar.setObjectName("settings_title_bar")
        tl = QHBoxLayout(title_bar)
        tl.setContentsMargins(16, 10, 16, 10)
        title_lbl = QLabel("\u2699  Settings")
        title_lbl.setObjectName("settings_title")
        tl.addWidget(title_lbl)
        root.addWidget(title_bar)

        _hline(root)

        # Tab button bar
        tab_bar = QWidget()
        tab_bar.setObjectName("settings_tab_bar")
        self._tab_layout = QHBoxLayout(tab_bar)
        self._tab_layout.setContentsMargins(8, 4, 8, 4)
        self._tab_layout.setSpacing(4)
        self._tab_layout.setAlignment(Qt.AlignLeft)
        root.addWidget(tab_bar)

        _hline(root)

        root.addWidget(self._stack, 1)

        _hline(root)

        # Footer
        footer = QWidget()
        footer.setObjectName("settings_footer")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(12, 8, 12, 8)
        fl.setSpacing(8)
        fl.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(32)
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("settings_save_btn")
        save_btn.setFixedHeight(32)
        save_btn.setMinimumWidth(90)
        save_btn.clicked.connect(self._on_save)
        fl.addWidget(cancel_btn)
        fl.addWidget(save_btn)
        root.addWidget(footer)

        # ── Register tabs here ──────────────────────────────────────────────
        # To add a new tab: self._add_tab("key", "Label", self._build_xxx_tab)
        self._add_tab("keys",     "Keys",     self._build_keys_tab)
        self._add_tab("model",    "Model",    self._build_model_tab)
        self._add_tab("agent",    "Agent",    self._build_agent_tab)
        self._add_tab("channels", "Channels", self._build_channels_tab)

        self._switch_tab("keys")

    # ── Tab system ────────────────────────────────────────────────────────────

    def _add_tab(self, key: str, label: str, builder):
        """Register a new tab. One call = one tab in the bar."""
        btn = QPushButton(label)
        btn.setObjectName("tab_btn")
        btn.setCheckable(True)
        btn.setFixedHeight(28)
        btn.clicked.connect(lambda _checked, k=key: self._switch_tab(k))
        self._tab_layout.addWidget(btn)
        self._tab_btns[key] = btn

        page = builder()
        self._stack.addWidget(page)
        self._tab_order.append(key)

    def _switch_tab(self, key: str):
        self._stack.setCurrentIndex(self._tab_order.index(key))
        for k, btn in self._tab_btns.items():
            btn.setChecked(k == key)

    # ── Layout helpers ────────────────────────────────────────────────────────

    def _scrollable_page(self) -> tuple[QScrollArea, QVBoxLayout]:
        """Returns (scroll_widget, content_layout) for a tab page."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("settings_scroll")
        content = QWidget()
        content.setObjectName("settings_page")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(content)
        return scroll, layout

    def _section(self, layout: QVBoxLayout, text: str):
        """Bold section header with a divider line."""
        lbl = QLabel(text.upper())
        lbl.setObjectName("settings_section_lbl")
        layout.addWidget(lbl)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)

    def _row(self, layout: QVBoxLayout, label: str, sublabel: str = "",
             widget_factory=None):
        """
        One settings row: label (+ optional sublabel) on the left, widget on the right.
        widget_factory(parent: QWidget) -> None  — creates & packs widget into parent.
        Pass widget_factory=None for label-only rows.
        """
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 5, 0, 5)
        rl.setSpacing(12)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(1)
        main_lbl = QLabel(label)
        main_lbl.setObjectName("settings_row_label")
        ll.addWidget(main_lbl)
        if sublabel:
            sub = QLabel(sublabel)
            sub.setObjectName("settings_row_sublabel")
            sub.setWordWrap(True)
            ll.addWidget(sub)

        rl.addWidget(left, 1)

        if widget_factory:
            right = QWidget()
            right.setObjectName("settings_row_right")
            widget_factory(right)
            rl.addWidget(right, 0)

        layout.addWidget(row)

    # ── Widget factories ──────────────────────────────────────────────────────

    def _attach(self, parent: QWidget, widget: QWidget):
        lay = QHBoxLayout(parent)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(widget)

    def _make_entry(self, parent: QWidget, value: str = "", placeholder: str = "",
                    secret: bool = False, enabled: bool = True, on_save=None):
        field = QLineEdit(value)
        field.setPlaceholderText(placeholder)
        field.setFixedWidth(220)
        field.setFixedHeight(28)
        if secret:
            field.setEchoMode(QLineEdit.Password)
        field.setEnabled(enabled)
        self._attach(parent, field)
        if on_save:
            self._save_actions.append(lambda f=field: on_save(f.text().strip()))

    def _make_combo(self, parent: QWidget, values: list[str], current: str = "",
                    enabled: bool = True, on_save=None):
        combo = QComboBox()
        combo.addItems(values)
        if current in values:
            combo.setCurrentText(current)
        combo.setFixedWidth(180)
        combo.setFixedHeight(28)
        combo.setEnabled(enabled)
        self._attach(parent, combo)
        if on_save:
            self._save_actions.append(lambda c=combo: on_save(c.currentText()))

    def _make_badge(self, parent: QWidget, text: str = "Soon"):
        """Placeholder badge for controls not yet implemented."""
        badge = QLabel(text)
        badge.setObjectName("settings_badge")
        self._attach(parent, badge)

    # ── Tab builders ──────────────────────────────────────────────────────────

    def _build_keys_tab(self) -> QScrollArea:
        scroll, lay = self._scrollable_page()
        self._key_fields: dict[str, QLineEdit] = {}

        self._section(lay, "API Keys")
        for key, label, placeholder, secret in _KEY_FIELDS:
            field = QLineEdit(keystore.get(key))
            field.setPlaceholderText(placeholder)
            field.setFixedWidth(220)
            field.setFixedHeight(28)
            if secret:
                field.setEchoMode(QLineEdit.Password)
            self._key_fields[key] = field
            self._row(lay, label, widget_factory=lambda p, f=field: self._attach(p, f))

        self._save_actions.append(self._save_keys)
        return scroll

    def _save_keys(self):
        keystore.save_all({k: f.text().strip() for k, f in self._key_fields.items()})

    def _build_model_tab(self) -> QScrollArea:
        scroll, lay = self._scrollable_page()

        self._section(lay, "Generation")
        self._row(lay, "Model",
                  "Which Gemini model to use.\nFlash — faster and cheaper. Pro — smarter, higher cost.\nRequires restart to take effect.",
                  lambda p: self._make_combo(p, _GEMINI_MODELS,
                                             current=config.get_chat_model(),
                                             on_save=config.set_chat_model))
        self._row(lay, "Temperature",
                  "Controls how creative the responses are.\n0.0 — precise and predictable. 1.0 — varied and creative.\nRecommended: 0.7 – 1.0.",
                  lambda p: self._make_entry(p, value=str(config.get_temperature()),
                                             on_save=lambda v: config.set_temperature(float(v))))
        self._row(lay, "Internet search",
                  "When the agent is allowed to search the web.\nauto — decides on its own. never — disabled.",
                  lambda p: self._make_combo(p, ["auto", "never"],
                                             current=config.get_internet_mode(),
                                             on_save=config.set_internet_mode))

        self._section(lay, "Context")
        self._row(lay, "History limit",
                  "How many recent messages are sent to the model as conversation context.\nMore = better memory, but higher cost per request.\nRecommended: 50 – 150.",
                  lambda p: self._make_entry(p, value=str(config.get_history_limit()),
                                             on_save=lambda v: config.set_history_limit(int(v))))

        return scroll

    def _build_agent_tab(self) -> QScrollArea:
        scroll, lay = self._scrollable_page()

        self._section(lay, "Execution Limits")
        self._row(lay, "Max tool iterations",
                  "Max steps the agent can take per request (read file, write, search, etc.).\nFor complex tasks like refactoring a project — increase this.\nRecommended: 10 – 20.",
                  lambda p: self._make_entry(p, value=str(config.get_max_tool_rounds()),
                                             on_save=lambda v: config.set_max_tool_rounds(int(v))))
        self._row(lay, "Max continuations",
                  "If the response was cut off mid-sentence (token limit hit) — how many times to auto-continue.\n0 = disabled. Recommended: 2 – 3.",
                  lambda p: self._make_entry(p, value=str(config.get_max_continuations()),
                                             on_save=lambda v: config.set_max_continuations(int(v))))
        self._row(lay, "Tool-first nudges",
                  "If the model replies with text instead of doing the action — how many times to push it to use tools.\nAlmost free in terms of tokens. Recommended: 5 – 7.",
                  lambda p: self._make_entry(p, value=str(config.get_max_tool_nudges()),
                                             on_save=lambda v: config.set_max_tool_nudges(int(v))))

        self._section(lay, "Loop Protection")
        self._row(lay, "Loop detection threshold",
                  "If the same tool is called with the same arguments N times in a row — the agent stops automatically.\nPrevents infinite loops. Recommended: 3.",
                  lambda p: self._make_entry(p, value=str(config.get_loop_detect_threshold()),
                                             on_save=lambda v: config.set_loop_detect_threshold(int(v))))
        self._row(lay, "Max result chars",
                  "If a tool result is too long (e.g. a huge file) — it gets trimmed to this many characters.\nPrevents context overflow. Recommended: 6000 – 12000.",
                  lambda p: self._make_entry(p, value=str(config.get_max_result_chars()),
                                             on_save=lambda v: config.set_max_result_chars(int(v))))

        self._section(lay, "Diary")
        self._row(lay, "Diary interval",
                  "How many messages (user + agent combined) between diary checks.\nA background thread reads the memory log and asks Ada to write a diary entry if something felt significant.\nRecommended: 50 – 200.",
                  lambda p: self._make_entry(p, value=str(config.get_diary_interval()),
                                             on_save=lambda v: config.set_diary_interval(int(v))))
        self._row(lay, "Load diary at startup",
                  "Whether to load DIARY.md into Ada's context at every startup.\non — Ada always remembers her diary entries.\noff — Ada can read the diary herself on demand via read_file.\nNote: large diary files will consume context space.",
                  lambda p: self._make_combo(p, ["off", "on"],
                                             current="on" if config.get_diary_load_at_startup() else "off",
                                             on_save=lambda v: config.set_diary_load_at_startup(v == "on")))

        return scroll

    def _build_channels_tab(self) -> QScrollArea:
        scroll, lay = self._scrollable_page()

        self._section(lay, "Telegram")
        self._row(lay, "Enabled", "Mirror chat via Telegram bot",
                  lambda p: self._make_badge(p))
        self._row(lay, "Send typing indicator", "Show typing status while thinking",
                  lambda p: self._make_badge(p))

        self._section(lay, "Future Channels")
        self._row(lay, "Discord", "Coming in a future episode",
                  lambda p: self._make_badge(p))

        return scroll
