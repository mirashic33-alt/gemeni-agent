"""
shell_tools.py — shell execution tools for the agent.

run_shell   — run a PowerShell command, return stdout/stderr/exit code
run_file    — launch a .py / .bat / .exe as a background process
list_processes — list processes started by the agent this session
kill_process   — stop a process by PID
"""

import os
import subprocess
import sys
import threading

# ── Dangerous command blacklist ───────────────────────────────────────────────

_BLOCKED = [
    "format ", "format/", "diskpart",
    "rm -rf", "rm -r /", "del /s", "del /f /s",
    "rd /s", "rmdir /s",
    "shutdown", "restart-computer",
    "reg delete", "regedit",
    "bcdedit", "bootrec",
    "cipher /w",
    "net user", "net localgroup",
    "taskkill /f /im",
    ":(){:|:&};:",   # fork bomb
]


def _is_blocked(cmd: str) -> str | None:
    low = cmd.lower()
    for pattern in _BLOCKED:
        if pattern in low:
            return pattern
    return None


def _ok(data: dict) -> dict:
    return {"status": "ok", **data}


def _err(msg: str) -> dict:
    return {"status": "error", "error": msg}


# ── Process registry (session-scoped) ─────────────────────────────────────────

_lock = threading.Lock()
_processes: dict[int, dict] = {}   # pid → {name, cmd, proc}


# ── Tools ─────────────────────────────────────────────────────────────────────

def run_shell(command: str, timeout: int = 60) -> dict:
    """
    Run a PowerShell command and return its output.
    Returns stdout, stderr, and exit code.
    timeout: max seconds to wait (default 60, max 300).
    Example: run_shell("Get-ChildItem C:/Users") or run_shell("python --version")
    """
    blocked = _is_blocked(command)
    if blocked:
        return _err(
            f"Command blocked for safety: contains '{blocked}'. "
            f"This operation is not permitted."
        )

    timeout = min(max(int(timeout), 1), 300)

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        return _ok({
            "exit_code": result.returncode,
            "stdout": stdout or "(no output)",
            "stderr": stderr or "",
        })
    except subprocess.TimeoutExpired:
        return _err(f"Command timed out after {timeout}s: {command!r}")
    except FileNotFoundError:
        return _err("PowerShell not found. Make sure it is installed.")
    except Exception as e:
        return _err(str(e))


def run_file(path: str, args: str = "") -> dict:
    """
    Launch a file as a background process. Supported: .py .bat .cmd .exe .ps1
    Returns the process PID. The process runs independently — use kill_process to stop it.
    path supports path aliases: workspace:, desktop:, documents:, downloads:, home:
    args: optional command-line arguments string.
    Example: run_file("workspace:script.py") or run_file("desktop:start.bat", "--debug")
    """
    from tools.file_tools import resolve_path

    real = resolve_path(path)
    if not os.path.exists(real):
        return _err(f"File not found: {path!r}")

    ext = os.path.splitext(real)[1].lower()
    if ext == ".py":
        cmd = [sys.executable, real]
    elif ext in (".bat", ".cmd"):
        cmd = ["cmd", "/c", real]
    elif ext == ".ps1":
        cmd = ["powershell", "-NoProfile", "-File", real]
    elif ext == ".exe":
        cmd = [real]
    else:
        return _err(f"Unsupported file type: {ext!r}. Supported: .py .bat .cmd .exe .ps1")

    if args:
        cmd += args.split()

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(real),
        )
        name = os.path.basename(real)
        with _lock:
            _processes[proc.pid] = {"name": name, "cmd": " ".join(cmd), "proc": proc}
        return _ok({"pid": proc.pid, "name": name, "message": f"Started: {name} (PID {proc.pid})"})
    except Exception as e:
        return _err(str(e))


def list_processes() -> dict:
    """
    List all processes started by the agent in this session, with their status.
    Example: list_processes()
    """
    with _lock:
        if not _processes:
            return _ok({"result": "No processes started in this session."})
        lines = []
        for pid, info in list(_processes.items()):
            proc = info["proc"]
            status = "running" if proc.poll() is None else f"exited ({proc.poll()})"
            lines.append(f"PID {pid}  [{status}]  {info['name']}")
        return _ok({"result": "\n".join(lines)})


def kill_process(pid: int) -> dict:
    """
    Stop a running process by PID. Only processes started by the agent can be stopped.
    Example: kill_process(12345)
    """
    with _lock:
        info = _processes.get(int(pid))
    if not info:
        return _err(f"PID {pid} not found in agent-started processes.")
    proc = info["proc"]
    if proc.poll() is not None:
        return _ok({"result": f"Process {pid} ({info['name']}) already exited."})
    try:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        return _ok({"result": f"Process {pid} ({info['name']}) terminated."})
    except Exception as e:
        return _err(str(e))


ALL_SHELL_TOOLS = [run_shell, run_file, list_processes, kill_process]
