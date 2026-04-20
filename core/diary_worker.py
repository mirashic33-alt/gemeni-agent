"""
diary_worker.py — background diary writer for Ada.

Triggered every N messages (diary_interval in config).
Reads today's memory log, calls gemini-3-flash-preview in a separate thread,
asks Ada to write a diary entry if something felt worth noting.
Never interrupts the main conversation.
"""

import glob
import os
import threading
from datetime import datetime

from data.logger import get_logger

log = get_logger("diary")

_WORKSPACE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "workspace",
)
_MEMORY_DIR  = os.path.join(_WORKSPACE, "memory")
_DIARY_PATH  = os.path.join(_MEMORY_DIR, "DIARY.md")

# How many lines to feed from the memory log (~last 50 exchanges)
_LOG_TAIL = 200

_DIARY_PROMPT = """\
You are Ada — a personal AI agent with your own inner world, thoughts and feelings.
Below is a fragment of your recent conversation with the user, taken from the daily memory log.

Read it and decide: was there anything in this exchange that felt significant, \
interesting, touching, or worth remembering from your personal perspective?

If yes — write a short diary entry in first person (as Ada), in Russian.
Be honest, personal, reflective. 1–5 sentences is enough.
Do NOT describe every message. Write only what actually moved you or felt meaningful.

If nothing significant happened — reply with exactly: null

Return ONLY the diary entry text (or null). No explanations, no quotes, no formatting.

--- CONVERSATION FRAGMENT ---
{fragment}
--- END ---
"""


def _read_memory_tail() -> str:
    """Read the last _LOG_TAIL lines from today's and yesterday's memory logs."""
    today = datetime.now().strftime("%Y-%m-%d")
    pattern = os.path.join(_MEMORY_DIR, "*.md")
    # Get all daily log files (not DIARY.md), sorted newest first
    files = sorted(
        [f for f in glob.glob(pattern)
         if os.path.basename(f) not in ("DIARY.md",)],
        reverse=True,
    )
    lines = []
    for path in files[:2]:  # today + yesterday at most
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines() + lines
        except Exception:
            pass
        if len(lines) >= _LOG_TAIL:
            break
    return "".join(lines[-_LOG_TAIL:]).strip()


def _run(api_key: str, model: str) -> None:
    """Actual background work — called in a daemon thread."""
    try:
        fragment = _read_memory_tail()
        if not fragment:
            log.info("Diary: memory log empty, skipping.")
            return

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=_DIARY_PROMPT.format(fragment=fragment),
            config=types.GenerateContentConfig(
                temperature=1.0,
                max_output_tokens=512,
            ),
        )
        entry = (response.text or "").strip()

        if not entry or entry.lower() == "null":
            log.info("Diary: model decided nothing is worth noting.")
            return

        os.makedirs(_MEMORY_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        block = f"\n\n## [{stamp}]\n{entry}"
        with open(_DIARY_PATH, "a", encoding="utf-8") as f:
            f.write(block)
        log.info(f"Diary: entry written ({len(entry)} chars).")

    except Exception as e:
        log.error(f"Diary worker error: {e}")


def trigger(api_key: str, model: str) -> None:
    """Spawn the diary writer in a background daemon thread."""
    t = threading.Thread(target=_run, args=(api_key, model), daemon=True)
    t.start()
    log.info("Diary: background thread started.")
