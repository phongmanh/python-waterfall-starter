"""Shared helpers for the waterfall hooks.

Standard library only, compatible with Python 3.9+ (the oldest python3 a Mac ships),
because hooks run before the project has an environment of its own.

* Parse ``docs/waterfall/STATUS.md`` (the phase table and change requests).
* Classify project paths by the phase that must be approved before they are written.
* Read hook input and emit hook decisions in Claude Code's JSON format.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional

STATUS_PATH = "docs/waterfall/STATUS.md"
STATE_DIR = ".claude/state"  # git-ignored; written by hooks only

PHASE_NAMES = {
    "P1": "Requirements",
    "P2": "Design",
    "P3": "Implementation",
    "P4": "Testing",
    "P5": "Deployment",
    "P6": "Maintenance",
}

OVERRIDE_NOTE = (
    "Only the user may override this gate (WATERFALL_GATE=off in "
    ".claude/settings.local.json). Do not edit STATUS.md, the hooks or the settings "
    "to get past it."
)


# --- hook I/O ----------------------------------------------------------------


def read_input() -> Dict[str, Any]:
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def project_dir(hook_input: Dict[str, Any]) -> Path:
    return Path(
        os.environ.get("CLAUDE_PROJECT_DIR") or hook_input.get("cwd") or os.getcwd()
    )


def gate_enabled() -> bool:
    return os.environ.get("WATERFALL_GATE", "").strip().lower() != "off"


def pretool_decision(decision: str, reason: str) -> NoReturn:
    """Emit a PreToolUse decision ("deny" or "ask") and exit."""
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


def add_context(event: str, text: str) -> NoReturn:
    """Inject text into Claude's context (SessionStart / UserPromptSubmit)."""
    out = {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


def run_safely(name: str, main: Any) -> None:
    """Never wedge a session on a hook bug: report it and fall back to normal flow."""
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - deliberate catch-all at the hook boundary
        sys.stderr.write(f"{name} hook error (ignored): {exc}\n")
        sys.exit(0)


# --- STATUS.md ---------------------------------------------------------------

_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _cells(line: str) -> List[str]:
    inner = line.strip().strip("|")
    return [_COMMENT.sub("", c).strip() for c in inner.split("|")]


def parse_status(text: str) -> Dict[str, Any]:
    """Parse STATUS.md. Tolerates partial files; missing parts come back empty."""
    result: Dict[str, Any] = {
        "current_phase": "",
        "project_status": "",
        "gate_policy": "",
        "phases": {},
        "change_requests": [],
    }
    section = ""
    for line in _COMMENT.sub("", text).splitlines():
        heading = re.match(r"^##\s+(.+)$", line)
        if heading:
            section = heading.group(1).strip().lower()
            continue
        if not line.strip().startswith("|"):
            continue
        cells = _cells(line)
        key = cells[0].lower() if cells else ""
        value = cells[1] if len(cells) > 1 else ""
        if key == "current phase":
            result["current_phase"] = value
        elif key == "project status":
            result["project_status"] = value
        elif key == "gate policy":
            result["gate_policy"] = value

        if section == "phases":
            m = re.match(r"^(P[1-6])\b", cells[0] if cells else "")
            if m:
                result["phases"][m.group(1)] = {
                    "name": cells[0],
                    "status": cells[2] if len(cells) > 2 else "",
                    "approved_on": cells[3] if len(cells) > 3 else "",
                }
        elif section == "change requests":
            if cells and re.match(r"^CR-\d+$", cells[0]):
                result["change_requests"].append(
                    {
                        "id": cells[0],
                        "change": cells[2] if len(cells) > 2 else "",
                        "status": cells[-1],
                    }
                )
    return result


def load_status(root: Path) -> Optional[Dict[str, Any]]:
    try:
        return parse_status((root / STATUS_PATH).read_text(encoding="utf-8"))
    except OSError:
        return None


def is_approved(value: str) -> bool:
    return bool(re.match(r"^approved\b", (value or "").strip(), re.I))


def phase_approved(status: Optional[Dict[str, Any]], phase: str) -> bool:
    if not status:
        return False
    return is_approved(status["phases"].get(phase, {}).get("status", ""))


def gates_waived(status: Optional[Dict[str, Any]]) -> bool:
    return bool(status and re.search(r"waiv", status.get("gate_policy", ""), re.I))


def open_change_requests(status: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    if not status:
        return []
    return [
        cr
        for cr in status["change_requests"]
        if not re.match(r"^(implemented|rejected)\b", cr["status"], re.I)
    ]


def awaiting_items(status: Optional[Dict[str, Any]]) -> List[str]:
    """IDs of phases awaiting approval and CRs proposed, e.g. ["P2", "CR-003"]."""
    if not status:
        return []
    items = [
        pid
        for pid, p in sorted(status["phases"].items())
        if re.match(r"^awaiting approval", p["status"], re.I)
    ]
    items += [
        cr["id"]
        for cr in status["change_requests"]
        if re.match(r"^proposed", cr["status"], re.I)
    ]
    return items


def label(item_id: str) -> str:
    """'P2' -> 'P2 Design'; CR IDs unchanged."""
    return f"{item_id} {PHASE_NAMES[item_id]}" if item_id in PHASE_NAMES else item_id


def approved_items(status: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Approved phases and CRs → their previous-state key, for diffing two versions."""
    if not status:
        return {}
    items = {
        pid: p["status"]
        for pid, p in status["phases"].items()
        if is_approved(p["status"])
    }
    for cr in status["change_requests"]:
        if re.match(r"^(approved|implemented)\b", cr["status"], re.I):
            items[cr["id"]] = cr["status"]
    return items


# --- paths -------------------------------------------------------------------


def relative_to_project(root: Path, file_path: str) -> Optional[str]:
    """Project-relative POSIX path, or None when the path is outside the project."""
    try:
        resolved = (root / file_path).resolve()
        rel = resolved.relative_to(root.resolve())
    except (ValueError, OSError):
        return None
    return rel.as_posix()


# First match wins, so the more specific rules come first.
_P4_FILES = re.compile(
    r"^(Dockerfile|Containerfile|\.dockerignore|(docker-)?compose(\.[\w-]+)?\.ya?ml"
    r"|fly\.toml|render\.ya?ml|Procfile|railway\.(json|toml)|app\.ya?ml|vercel\.json"
    r"|serverless\.ya?ml)$"
)
_P4_DIRS = re.compile(r"^(deploy|k8s|helm|infra|terraform)(/|$)")
_P2_DIRS = re.compile(r"^(src|tests|migrations|alembic|scripts)(/|$)")
_P2_FILES = re.compile(
    r"^(pyproject\.toml|uv\.lock|poetry\.lock|pdm\.lock|requirements[\w.-]*\.(txt|in)"
    r"|setup\.(py|cfg)|\.python-version|\.pre-commit-config\.ya?ml|Makefile|justfile"
    r"|noxfile\.py|tox\.ini|alembic\.ini|conftest\.py|mypy\.ini|\.?ruff\.toml"
    r"|pytest\.ini|\.env\.example|MANIFEST\.in)$"
)
_UNGATED = re.compile(r"^(docs|\.claude)/")
GUARDRAIL_FILES = re.compile(
    r"^\.claude/(settings(\.local)?\.json|hooks/.*|agents/.*)$"
)


def required_phase_for(rel: str) -> Optional[str]:
    """The phase that must be approved before `rel` may be written, or None."""
    p = rel[2:] if rel.startswith("./") else rel
    if p.startswith(".github/workflows/"):
        return None if re.search(r"/claude-hooks\.ya?ml$", p) else "P4"
    if _P4_FILES.match(p) or _P4_DIRS.match(p):
        return "P4"
    if _UNGATED.match(p):
        return None
    if _P2_DIRS.match(p) or _P2_FILES.match(p) or re.search(r"\.(py|pyi|ipynb)$", p):
        return "P2"
    return None


def describe_phase(status: Optional[Dict[str, Any]], phase: str) -> str:
    if not status:
        return f"no waterfall project has been started ({STATUS_PATH} does not exist)"
    value = status["phases"].get(phase, {}).get("status") or "missing"
    return f'Phase {phase[1:]} ({PHASE_NAMES[phase]}) is "{value}" in {STATUS_PATH}'


def next_phase(phase: str) -> str:
    return f"P{int(phase[1:]) + 1}"
