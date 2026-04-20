"""
names.py — reads agent and user names from workspace memory files.

Parses **Name:** field from SOUL.md and USER.md.
Falls back to defaults if files are missing or name not set yet.
Call refresh() after the model updates the files mid-session.
"""

import os
import re

_WORKSPACE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "workspace",
)

_DEFAULT_AGENT = "Gemeni"
_DEFAULT_USER  = "You"

_agent_name: str = _DEFAULT_AGENT
_user_name:  str = _DEFAULT_USER


def _parse_name(path: str) -> str | None:
    """Extract **Name:** value from a markdown file."""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        m = re.search(r'\*\*Name:\*\*\s*(.+)', content)
        if m:
            name = m.group(1).strip()
            if name:
                return name
    except Exception:
        pass
    return None


def refresh() -> None:
    """Re-read names from disk. Call at startup and after model updates the files."""
    global _agent_name, _user_name

    name = _parse_name(os.path.join(_WORKSPACE, "SOUL.md"))
    _agent_name = name if name else _DEFAULT_AGENT

    name = _parse_name(os.path.join(_WORKSPACE, "USER.md"))
    _user_name = name if name else _DEFAULT_USER


def get_agent_name() -> str:
    return _agent_name


def get_user_name() -> str:
    return _user_name


# Load names immediately on import
refresh()
