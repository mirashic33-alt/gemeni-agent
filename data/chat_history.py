"""
chat_history.py — save and load chat history.
File: workspace/chat_history.json
Stores the last _limit() messages.
"""

import json
import os
from datetime import datetime

_MAX_MSG_CHARS = 15_000  # messages longer than this are not saved to history


def _limit() -> int:
    try:
        import data.config as config
        return config.get_history_limit()
    except Exception:
        return 100
HISTORY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "workspace", "chat_history.json"
)


def _ensure_dir():
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)


def _sanitize(messages: list[dict]) -> list[dict]:
    """Remove broken tails from messages that were hard-cut by _MAX_MSG_CHARS.
    An unterminated sentence in history triggers the model to 'continue' it → loop.
    """
    _TRUNC_MARKER = "[обрезано: слишком длинное сообщение]"
    for msg in messages:
        text = msg.get("text", "")
        if _TRUNC_MARKER in text:
            # Strip the marker and everything after the last sentence boundary
            idx = text.find(_TRUNC_MARKER)
            clean = text[:idx].rstrip()
            # Find the last sentence end (., !, ?, \n)
            last_end = max(
                clean.rfind("."), clean.rfind("!"),
                clean.rfind("?"), clean.rfind("\n"),
            )
            if last_end > len(clean) // 2:
                clean = clean[:last_end + 1]
            msg["text"] = clean
    return messages


def load() -> list[dict]:
    """Loads history from file. Returns a list of messages."""
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return _sanitize(data[-_limit():])
    except Exception:
        pass
    return []


def append(role: str, text: str) -> list[dict]:
    """
    Appends a message and saves the file.
    role: "user" | "agent"
    Returns the updated list.
    """
    if len(text) > _MAX_MSG_CHARS:
        text = text[:_MAX_MSG_CHARS] + "\n...[обрезано: слишком длинное сообщение]"
    messages = load()
    messages.append({
        "role": role,
        "text": text,
        "ts": datetime.now().strftime("%H:%M"),
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
    if len(messages) > _limit():
        messages = messages[-_limit():]
    _save(messages)
    return messages


def clear() -> None:
    """Erases the history file."""
    _ensure_dir()
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump([], f)


def _save(messages: list[dict]) -> None:
    _ensure_dir()
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
