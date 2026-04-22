"""
config.py — persistent agent settings.
File: data/config.json (plain JSON, human-readable, editable by the agent too).
"""

import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

_DEFAULTS: dict = {
    # LLM
    "chat_model":     "gemini-3-flash-preview",
    "temperature":    0.9,
    "max_output_tokens": 4096,   # max tokens per single model response (~3000 words)
    "internet_mode":  "auto",   # "auto" | "always" | "never"
    # Context
    "history_limit":  100,
    # Agent (Episode 2+)
    "max_tool_rounds":       10,
    "max_continuations":      0,
    "max_tool_nudges":         5,
    "loop_detect_threshold":  3,
    "max_result_chars":    8000,
    "diary_interval":        100,  # messages between diary checks
    "diary_load_at_startup": False, # load DIARY.md into system prompt at startup
}

_cache: dict = {}


def _load() -> dict:
    if not os.path.exists(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save() -> None:
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(_cache, f, ensure_ascii=False, indent=2)


def load() -> None:
    """Call once at startup to load config into memory."""
    global _cache
    _cache = {**_DEFAULTS, **_load()}


def get(key: str):
    """Returns the current value, falling back to defaults."""
    return _cache.get(key, _DEFAULTS.get(key))


def set(key: str, value) -> None:
    """Updates a single value and persists to disk."""
    _cache[key] = value
    _save()


def set_many(data: dict) -> None:
    """Updates multiple values at once and persists to disk."""
    _cache.update(data)
    _save()


# ── Typed accessors ───────────────────────────────────────────────────────────

def get_chat_model() -> str:        return get("chat_model")
def set_chat_model(v: str):         set("chat_model", v)

def get_temperature() -> float:     return float(get("temperature"))
def set_temperature(v: float):      set("temperature", v)

def get_internet_mode() -> str:     return get("internet_mode")
def set_internet_mode(v: str):      set("internet_mode", v)

def get_history_limit() -> int:     return int(get("history_limit"))
def set_history_limit(v: int):      set("history_limit", v)

def get_max_tool_rounds() -> int:         return int(get("max_tool_rounds"))
def set_max_tool_rounds(v: int):          set("max_tool_rounds", v)

def get_max_continuations() -> int:       return int(get("max_continuations"))
def set_max_continuations(v: int):        set("max_continuations", v)

def get_max_tool_nudges() -> int:         return int(get("max_tool_nudges"))
def set_max_tool_nudges(v: int):          set("max_tool_nudges", v)

def get_loop_detect_threshold() -> int:   return int(get("loop_detect_threshold"))
def set_loop_detect_threshold(v: int):    set("loop_detect_threshold", v)

def get_max_result_chars() -> int:        return int(get("max_result_chars"))
def set_max_result_chars(v: int):         set("max_result_chars", v)

def get_diary_interval() -> int:          return int(get("diary_interval"))
def set_diary_interval(v: int):           set("diary_interval", v)

def get_diary_load_at_startup() -> bool:  return bool(get("diary_load_at_startup"))
def set_diary_load_at_startup(v: bool):   set("diary_load_at_startup", v)
