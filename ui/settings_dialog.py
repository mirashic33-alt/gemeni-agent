import data.keystore as keystore
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame
)
from PySide6.QtCore import Qt

FIELDS = [
    ("GEMINI_API_KEY",   "Gemini API Key",      "Paste your Google AI Studio key...",  True),
    ("TELEGRAM_TOKEN",   "Telegram Bot Token",  "Paste token from @BotFather...",      True),
    ("TELEGRAM_CHAT_ID", "Telegram Chat ID",    "Your numeric chat_id...",             False),
]


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(440)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Agent Settings")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)

        self._fields: dict[str, QLineEdit] = {}
        for key, label_text, placeholder, secret in FIELDS:
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 12px;")
            field = QLineEdit()
            field.setPlaceholderText(placeholder)
            field.setText(keystore.get(key))
            if secret:
                field.setEchoMode(QLineEdit.Password)
            self._fields[key] = field
            layout.addWidget(lbl)
            layout.addWidget(field)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.save_btn   = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn.setFixedHeight(34)
        self.cancel_btn.setFixedHeight(34)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn.clicked.connect(self.reject)

    def _on_save(self):
        data = {key: field.text().strip() for key, field in self._fields.items()}
        keystore.save_all(data)
        self.accept()
