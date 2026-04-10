"""
system_monitor.py — real-time system resource monitoring.
Requires: pip install psutil
"""

import psutil


def get_system_stats() -> str:
    """
    Returns a status bar string:
    CPU: 23%  |  RAM: 64%  |  C: 93.1GB
    """
    cpu = psutil.cpu_percent(interval=None)

    ram = psutil.virtual_memory()
    ram_pct = ram.percent

    try:
        disk = psutil.disk_usage("C:\\")
        disk_free_gb = disk.free / (1024 ** 3)
        disk_str = f"C: {disk_free_gb:.1f}GB"
    except Exception:
        disk_str = "C: —"

    return f"CPU: {cpu:.0f}%  |  RAM: {ram_pct:.0f}%  |  {disk_str}"
