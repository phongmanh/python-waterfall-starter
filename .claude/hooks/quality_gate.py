#!/usr/bin/env python3
"""Stop hook: refuses to end the turn while Python code changed since the last green
check fails `ruff format --check`, `ruff check` or `mypy` (the waterfall rule: never
stack work on a red build). Tests are not run here: `make check` runs them per module.

Inactive until the project environment exists (.venv/bin/ruff, created in Phase 3).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List

from _waterfall import project_dir, read_input, run_safely

WATCHED_DIRS = ("src", "tests")
WATCHED_FILES = ("pyproject.toml", "uv.lock")
STAMP = Path(".venv") / ".claude-quality-gate.stamp"


def tool(root: Path, name: str) -> Path:
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    return root / ".venv" / scripts / (f"{name}.exe" if sys.platform == "win32" else name)


def changed_since_stamp(root: Path) -> bool:
    stamp = root / STAMP
    if not stamp.exists():
        return True
    since = stamp.stat().st_mtime
    files: List[Path] = [root / f for f in WATCHED_FILES]
    for d in WATCHED_DIRS:
        files.extend(f for f in (root / d).rglob("*.py*") if f.suffix in (".py", ".pyi"))
    return any(f.exists() and f.stat().st_mtime > since for f in files)


def run(cmd: List[str], root: Path) -> str:
    """Output of a failing command, or '' when it passes."""
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=150, check=False)
    if proc.returncode == 0:
        return ""
    return (proc.stdout + proc.stderr).strip() or f"exited with code {proc.returncode}"


def tail(text: str, n: int = 40) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-n:])


def main() -> None:
    hook_input = read_input()
    if hook_input.get("stop_hook_active"):
        return  # already continuing because of this hook; don't loop
    root = project_dir(hook_input)
    ruff, mypy = tool(root, "ruff"), tool(root, "mypy")
    if not ruff.exists() or not any((root / d).is_dir() for d in WATCHED_DIRS):
        return
    if not changed_since_stamp(root):
        return

    problems = []
    out = run([str(ruff), "format", "--check", "."], root)
    if out:
        problems.append("ruff format --check failed (run `make fmt`):\n" + tail(out, 20))
    out = run([str(ruff), "check", "--output-format=concise", "."], root)
    if out:
        problems.append("ruff check failed:\n" + tail(out))
    if mypy.exists():
        out = run([str(mypy)], root)
        if out:
            problems.append("mypy failed:\n" + tail(out))

    if problems:
        sys.stderr.write(
            "Quality gate failed. Fix this before ending the turn (waterfall rule: never "
            "stack work on a red build).\n\n" + "\n\n".join(problems) + "\n"
        )
        sys.exit(2)
    (root / STAMP).touch()


if __name__ == "__main__":
    run_safely("quality-gate", main)
