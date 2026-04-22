"""
file_tools.py — file system tools for the agent.

Path aliases:
  desktop:   → user Desktop
  documents: → user Documents
  downloads: → user Downloads
  workspace: → project workspace/
  home:      → user home directory
"""

import os
import shutil
import fnmatch

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_ALIASES: dict[str, str] = {
    "desktop:":   os.path.join(os.path.expanduser("~"), "Desktop"),
    "documents:": os.path.join(os.path.expanduser("~"), "Documents"),
    "downloads:": os.path.join(os.path.expanduser("~"), "Downloads"),
    "workspace:": os.path.join(_PROJECT_ROOT, "workspace"),
    "home:":      os.path.expanduser("~"),
}


def resolve_path(path: str) -> str:
    """Expands a path alias to an absolute path."""
    for alias, real in _ALIASES.items():
        if path.lower().startswith(alias):
            tail = path[len(alias):].lstrip("/\\")
            return os.path.join(real, tail) if tail else real
    return path


def _ok(data: str) -> dict:
    return {"status": "ok", "result": data}


def _err(msg: str) -> dict:
    return {"status": "error", "error": msg}


# ── Tools ─────────────────────────────────────────────────────────────────────

def list_files(path: str) -> dict:
    """
    List files and folders inside a directory.
    Supports path aliases: desktop:, workspace:, documents:, downloads:, home:.
    Example: list_files("workspace:") or list_files("desktop:projects")
    """
    try:
        real = resolve_path(path)
        if not os.path.exists(real):
            return _err(f"Path not found: {path!r}")
        if not os.path.isdir(real):
            return _err(f"Not a directory: {path!r}")
        lines = []
        for name in sorted(os.listdir(real)):
            full = os.path.join(real, name)
            if os.path.isdir(full):
                lines.append(f"[dir]  {name}/")
            else:
                size = os.path.getsize(full)
                lines.append(f"[file] {name}  ({size:,} bytes)")
        return _ok("\n".join(lines) if lines else "(empty directory)")
    except PermissionError:
        return _err(f"Access denied: {path!r}")
    except Exception as e:
        return _err(str(e))


def read_file(path: str) -> dict:
    """
    Read the text content of a file and return it.
    Supports path aliases: desktop:, workspace:, documents:, downloads:, home:.
    Example: read_file("workspace:notes.txt")
    """
    try:
        real = resolve_path(path)
        if not os.path.exists(real):
            return _err(f"File not found: {path!r}")
        if not os.path.isfile(real):
            return _err(f"Not a file: {path!r}")
        with open(real, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return _ok(content)
    except PermissionError:
        return _err(f"Access denied: {path!r}")
    except Exception as e:
        return _err(str(e))


def write_file(path: str, content: str) -> dict:
    """
    Create a new file or completely overwrite an existing one with the given content.
    Supports path aliases: desktop:, workspace:, documents:, downloads:, home:.
    Example: write_file("workspace:hello.txt", "Hello, world!")
    """
    try:
        real = resolve_path(path)
        os.makedirs(os.path.dirname(real) or ".", exist_ok=True)
        with open(real, "w", encoding="utf-8") as f:
            f.write(content)
        return _ok(f"Written {len(content):,} chars → {path!r}")
    except PermissionError:
        return _err(f"Access denied: {path!r}")
    except Exception as e:
        return _err(str(e))


def append_file(path: str, content: str) -> dict:
    """
    Append text to the end of a file without touching existing content.
    Creates the file if it does not exist.
    Supports path aliases: desktop:, workspace:, documents:, downloads:, home:.
    Example: append_file("workspace:log.txt", "\\nNew line")
    """
    try:
        real = resolve_path(path)
        os.makedirs(os.path.dirname(real) or ".", exist_ok=True)
        with open(real, "a", encoding="utf-8") as f:
            f.write(content)
        return _ok(f"Appended {len(content):,} chars → {path!r}")
    except PermissionError:
        return _err(f"Access denied: {path!r}")
    except Exception as e:
        return _err(str(e))


def create_dir(path: str) -> dict:
    """
    Create a directory, including any missing parent directories.
    Supports path aliases: desktop:, workspace:, documents:, downloads:, home:.
    Example: create_dir("workspace:projects/new_project")
    """
    try:
        real = resolve_path(path)
        os.makedirs(real, exist_ok=True)
        return _ok(f"Directory ready: {path!r}")
    except PermissionError:
        return _err(f"Access denied: {path!r}")
    except Exception as e:
        return _err(str(e))


def patch_file(path: str, old_text: str, new_text: str) -> dict:
    """
    Replace the first occurrence of old_text with new_text in a file.
    Use this instead of write_file when editing a small part of a large file.
    Supports path aliases: desktop:, workspace:, documents:, downloads:, home:.
    Example: patch_file("workspace:notes.txt", "old line", "new line")
    """
    try:
        real = resolve_path(path)
        if not os.path.exists(real):
            return _err(f"File not found: {path!r}")
        with open(real, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if old_text not in content:
            return _err(f"Text not found in file: {old_text!r}")
        patched = content.replace(old_text, new_text, 1)
        with open(real, "w", encoding="utf-8") as f:
            f.write(patched)
        return _ok(f"Patched {path!r}: replaced 1 occurrence.")
    except PermissionError:
        return _err(f"Access denied: {path!r}")
    except Exception as e:
        return _err(str(e))


def delete_file(path: str) -> dict:
    """
    Delete a file or an empty/non-empty directory. Moves to recycle bin if possible,
    otherwise deletes permanently. Use with caution.
    Supports path aliases: desktop:, workspace:, documents:, downloads:, home:.
    Example: delete_file("workspace:old_notes.txt")
    """
    try:
        real = resolve_path(path)
        if not os.path.exists(real):
            return _err(f"Not found: {path!r}")
        try:
            import send2trash
            send2trash.send2trash(real)
            return _ok(f"Moved to recycle bin: {path!r}")
        except ImportError:
            pass
        if os.path.isdir(real):
            shutil.rmtree(real)
        else:
            os.remove(real)
        return _ok(f"Deleted permanently (send2trash not installed): {path!r}")
    except PermissionError:
        return _err(f"Access denied: {path!r}")
    except Exception as e:
        return _err(str(e))


def rename_file(path: str, new_name: str) -> dict:
    """
    Rename a file or directory. new_name is just the name, not a full path.
    Supports path aliases: desktop:, workspace:, documents:, downloads:, home:.
    Example: rename_file("workspace:old.txt", "new.txt")
    """
    try:
        real = resolve_path(path)
        if not os.path.exists(real):
            return _err(f"Not found: {path!r}")
        parent = os.path.dirname(real)
        dest = os.path.join(parent, new_name)
        if os.path.exists(dest):
            return _err(f"Target already exists: {new_name!r}")
        os.rename(real, dest)
        return _ok(f"Renamed {path!r} → {new_name!r}")
    except PermissionError:
        return _err(f"Access denied: {path!r}")
    except Exception as e:
        return _err(str(e))


def move_file(path: str, dest_path: str) -> dict:
    """
    Move a file or directory to a new location.
    Supports path aliases for both arguments.
    Example: move_file("workspace:draft.txt", "desktop:final.txt")
    """
    try:
        real_src = resolve_path(path)
        real_dst = resolve_path(dest_path)
        if not os.path.exists(real_src):
            return _err(f"Source not found: {path!r}")
        os.makedirs(os.path.dirname(real_dst) or ".", exist_ok=True)
        shutil.move(real_src, real_dst)
        return _ok(f"Moved {path!r} → {dest_path!r}")
    except PermissionError:
        return _err(f"Access denied.")
    except Exception as e:
        return _err(str(e))


def search_files(path: str, pattern: str) -> dict:
    """
    Search for files matching a name pattern inside a directory (recursive).
    pattern supports wildcards: *.py, *.md, report*.txt, etc.
    Supports path aliases: desktop:, workspace:, documents:, downloads:, home:.
    Example: search_files("desktop:", "*.py") or search_files("workspace:", "notes*")
    """
    try:
        real = resolve_path(path)
        if not os.path.exists(real):
            return _err(f"Path not found: {path!r}")
        if not os.path.isdir(real):
            return _err(f"Not a directory: {path!r}")
        matches = []
        for root, dirs, files in os.walk(real):
            dirs.sort()
            for name in sorted(files):
                if fnmatch.fnmatch(name.lower(), pattern.lower()):
                    rel = os.path.relpath(os.path.join(root, name), real)
                    size = os.path.getsize(os.path.join(root, name))
                    matches.append(f"{rel}  ({size:,} bytes)")
        if not matches:
            return _ok(f"No files matching {pattern!r} found in {path!r}")
        return _ok(f"Found {len(matches)} file(s):\n" + "\n".join(matches))
    except PermissionError:
        return _err(f"Access denied: {path!r}")
    except Exception as e:
        return _err(str(e))


_TREE_SKIP = {"__pycache__", "node_modules"}
_TREE_SKIP_EXT = {".pyc"}


def get_project_tree() -> dict:
    """
    Returns the full file and folder tree of the agent project, starting from the project root.
    Use this when you need to find a file path or understand the project structure.
    Call this FIRST instead of searching blindly with other tools.
    """
    root = _PROJECT_ROOT
    project_name = os.path.basename(root)
    lines = [f"📁 {project_name}/  ← project root"]
    try:
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in _TREE_SKIP)
            depth = os.path.relpath(dirpath, root).count(os.sep)
            if dirpath != root:
                indent = "  " * depth
                lines.append(f"{indent}📁 {os.path.basename(dirpath)}/")
            file_indent = "  " * (depth + 1)
            for fname in sorted(files):
                if os.path.splitext(fname)[1].lower() not in _TREE_SKIP_EXT:
                    lines.append(f"{file_indent}📄 {fname}")
    except Exception as e:
        return _err(str(e))
    return _ok("\n".join(lines))


ALL_TOOLS = [
    list_files, read_file, write_file, append_file, create_dir,
    patch_file, delete_file, rename_file, move_file, search_files,
    get_project_tree,
]
