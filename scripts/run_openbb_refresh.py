"""Locate the cached OpenBB MCP environment and refresh the US macro snapshot."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def discover_openbb_python(uv_cache: Path) -> Path:
    candidates = []
    for executable in uv_cache.glob("archive-v0/*/Scripts/openbb-mcp.exe"):
        python = executable.with_name("python.exe")
        if python.exists():
            candidates.append(python)
    if not candidates:
        raise FileNotFoundError(
            f"No OpenBB MCP Python environment found under {uv_cache}. "
            "Set OPENBB_PYTHON to its python.exe."
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def main() -> None:
    configured = os.environ.get("OPENBB_PYTHON")
    if configured:
        python = Path(configured)
    else:
        local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        python = discover_openbb_python(local_app_data / "uv" / "cache")
    if not python.exists():
        raise FileNotFoundError(f"OpenBB Python not found: {python}")

    command = [
        str(python),
        "-m",
        "scripts.refresh_openbb_us_macro",
        *sys.argv[1:],
    ]
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
