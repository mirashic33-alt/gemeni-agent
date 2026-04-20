"""
daily_log.py — appends every message to workspace/memory/YYYY-MM-DD.md.

One file per day. Written automatically, no model involvement.
The model can read these files manually via read_file() when needed.
"""

import os
from datetime import datetime

_MEMORY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "workspace", "memory",
)


def _today_path() -> str:
    date_str = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(_MEMORY_DIR, f"{date_str}.md")


def append_message(role: str, text: str) -> None:
    """
    Append one message to today's log file.
    role: "user" | "agent"
    """
    if not text or not text.strip():
        return
    try:
        os.makedirs(_MEMORY_DIR, exist_ok=True)
        path = _today_path()
        ts = datetime.now().strftime("%H:%M")
        from core.names import get_agent_name, get_user_name
        label = get_user_name() if role == "user" else get_agent_name()
        block = f"## [{ts}] {label}\n{text.strip()}\n\n---\n\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(block)
    except Exception:
        pass  # log errors silently — never crash the UI
