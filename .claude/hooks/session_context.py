#!/usr/bin/env python3
"""SessionStart hook: tells Claude where the waterfall project stands, so a new,
resumed, cleared or compacted session continues the right phase instead of guessing."""

from __future__ import annotations

from _waterfall import (
    PHASE_NAMES,
    STATUS_PATH,
    add_context,
    awaiting_items,
    gate_enabled,
    gates_waived,
    label,
    load_status,
    open_change_requests,
    project_dir,
    read_input,
    run_safely,
)


def main() -> None:
    status = load_status(project_dir(read_input()))
    if not status:
        add_context(
            "SessionStart",
            f"Waterfall: no project started yet ({STATUS_PATH} is missing). When the user "
            "asks to build something, use the python-waterfall skill and begin Phase 1 "
            "(Requirements) in this repository's root.",
        )

    lines = [f"Waterfall status ({STATUS_PATH}):"]
    if status["project_status"]:
        lines.append(f"- Project: {status['project_status']}")
    if status["current_phase"]:
        lines.append(f"- Current phase: {status['current_phase']}")
    for pid, name in PHASE_NAMES.items():
        p = status["phases"].get(pid)
        if p:
            approved = f" (approved {p['approved_on']})" if p["approved_on"] else ""
            lines.append(f"- {pid} {name}: {p['status'] or 'unknown'}{approved}")
    if gates_waived(status):
        lines.append(f"- Gate policy: {status['gate_policy']}")
    if not gate_enabled():
        lines.append("- WATERFALL_GATE=off: the user has disabled the phase-gate hooks.")
    crs = open_change_requests(status)
    if crs:
        lines.append("- Open change requests: " + ", ".join(f"{c['id']} ({c['status']})" for c in crs))
    waiting = awaiting_items(status)
    if waiting:
        lines.append(
            f"Awaiting the user's sign-off: {', '.join(label(i) for i in waiting)}. Do not "
            "start the next phase or implement the CR until they explicitly approve."
        )
    else:
        lines.append(
            "Continue with the python-waterfall skill. Re-read the approved documents "
            "before working on the current phase."
        )
    add_context("SessionStart", "\n".join(lines))


if __name__ == "__main__":
    run_safely("session-context", main)
