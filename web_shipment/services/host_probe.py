"""Host reachability probes used by network tests."""

from __future__ import annotations

import platform
import subprocess


def is_host_up(host: str, timeout_seconds: int = 1) -> bool:
    """Return True when one ICMP probe reaches the host."""
    if platform.system().lower().startswith("win"):
        cmd = ["ping", "-n", "1", "-w", str(timeout_seconds * 1000), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(timeout_seconds), host]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0
