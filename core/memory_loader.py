"""
memory_loader.py — loads workspace memory files into the system prompt.

Files loaded at every startup (in order):
  workspace/agent.md    — rules, tools, behaviour
  workspace/MEMORY.md   — long-term facts about user and project
  workspace/USER.md     — facts about the user (filled by the agent)
  workspace/SOUL.md     — agent personality and name (filled by the agent)
  workspace/skills/*.md — agent skills, one file per skill (filled by the agent)
"""

import glob
import os

_WORKSPACE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "workspace",
)

_MEMORY_FILES = [
    ("agent.md",  "AGENT"),
    ("MEMORY.md", "MEMORY"),
    ("USER.md",   "USER"),
    ("SOUL.md",   "SOUL"),
]

_TIME_RULE = (
    "Each user message starts with the current date and time in brackets "
    "(e.g. [19.04.2026, Sunday, 15:14]). "
    "Use it silently for temporal orientation. "
    "Never repeat or draw attention to the timestamp unless explicitly asked."
)


def _workspace_tree() -> str:
    """
    Returns a text tree of workspace/ so the agent knows all paths at startup.
    Skips binary files and very large folders.
    """
    lines = [f"workspace: = {_WORKSPACE}"]
    try:
        for root, dirs, files in os.walk(_WORKSPACE):
            dirs[:] = sorted(d for d in dirs if not d.startswith((".", "__")))
            depth = root.replace(_WORKSPACE, "").count(os.sep)
            indent = "  " * depth
            folder = os.path.basename(root)
            if depth > 0:
                lines.append(f"{indent}[dir]  {folder}/")
            for fname in sorted(files):
                lines.append(f"{'  ' * (depth + 1)}[file] {fname}")
    except Exception:
        pass
    return "\n".join(lines)


def _load_skills() -> str:
    """Scans workspace/skills/*.md and returns all skill content as one block."""
    skills_dir = os.path.join(_WORKSPACE, "skills")
    if not os.path.isdir(skills_dir):
        return ""
    parts = []
    for path in sorted(glob.glob(os.path.join(skills_dir, "*.md"))):
        try:
            content = open(path, encoding="utf-8").read().strip()
            if content:
                name = os.path.basename(path)
                parts.append(f"--- SKILL: {name} ---\n{content}")
        except Exception:
            pass
    return "\n\n".join(parts)


def build_system_prompt() -> str:
    """
    Reads memory files and assembles the full system prompt.
    Missing files are skipped silently (MEMORY.md and skills may not exist yet).
    """
    sections: list[str] = []

    for filename, label in _MEMORY_FILES:
        path = os.path.join(_WORKSPACE, filename)
        if os.path.exists(path):
            try:
                content = open(path, encoding="utf-8").read().strip()
                if content:
                    sections.append(f"--- {label} ---\n{content}")
            except Exception as e:
                sections.append(f"--- {label} --- (load error: {e})")

    skills_block = _load_skills()
    if skills_block:
        sections.append(skills_block)

    # Optionally load diary into system prompt
    import data.config as config
    if config.get_diary_load_at_startup():
        diary_path = os.path.join(_WORKSPACE, "memory", "DIARY.md")
        if os.path.exists(diary_path):
            try:
                content = open(diary_path, encoding="utf-8").read().strip()
                if content:
                    sections.append(f"--- DIARY ---\n{content}")
            except Exception:
                pass

    sections.append(f"--- TIME ---\n{_TIME_RULE}")

    tree = _workspace_tree()
    if tree:
        sections.append(
            f"--- WORKSPACE STRUCTURE ---\n"
            f"Your workspace folder structure at startup (use these paths directly):\n\n"
            f"{tree}"
        )

    return "\n\n".join(sections)
