#!/usr/bin/env python3
"""PostToolUse hook: after Claude writes or edits a Python file, apply ruff's safe
fixes, format it with `ruff format`, and report what is left. Remaining lint errors
go back to Claude (exit 2 + stderr) so they are fixed now, not at `make check`.

Inactive until the project environment exists (.venv/bin/ruff, created in Phase 3).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from _waterfall import project_dir, read_input, relative_to_project, run_safely

PY_FILE = re.compile(r"\.pyi?$")
SKIP = re.compile(r"^(docs|\.claude|\.venv|build|dist)/")


def ruff_path(root: Path) -> Path:
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    exe = "ruff.exe" if sys.platform == "win32" else "ruff"
    return root / ".venv" / scripts / exe


def run(cmd: list, cwd: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=45, check=False)


def main() -> None:
    hook_input = read_input()
    root = project_dir(hook_input)
    file_path = (hook_input.get("tool_input") or {}).get("file_path")
    if not file_path:
        return
    rel = relative_to_project(root, file_path)
    ruff = ruff_path(root)
    if not rel or SKIP.match(rel) or not PY_FILE.search(rel) or not ruff.exists():
        return
    if not (root / rel).exists():
        return

    # Fix first, then format (ruff's recommended order), then report what's left.
    problems = []
    run([str(ruff), "check", "--fix", "--quiet", rel], root)
    fmt = run([str(ruff), "format", "--quiet", rel], root)
    if fmt.returncode != 0:
        problems.append(f"ruff format could not format {rel}:\n{fmt.stdout}{fmt.stderr}")
    lint = run([str(ruff), "check", "--quiet", "--output-format=concise", rel], root)
    if lint.returncode != 0:
        problems.append(f"ruff check found problems in {rel}:\n{lint.stdout}{lint.stderr}")

    if problems:
        sys.stderr.write("\n\n".join(p.strip() for p in problems) + "\n\nFix these before continuing.\n")
        sys.exit(2)


if __name__ == "__main__":
    run_safely("format-lint", main)
