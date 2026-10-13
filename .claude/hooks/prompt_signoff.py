#!/usr/bin/env python3
"""UserPromptSubmit hook: decides whether the user's message is an explicit sign-off.

When a phase or CR is awaiting approval, it tells Claude whether the message reads as an
unconditional approval, so gates are neither skipped nor stalled. It also records the
verdict in .claude/state/approval.json, which phase_gate.py's approval guard checks
before STATUS.md may mark anything as approved.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from _waterfall import (
    STATE_DIR,
    add_context,
    awaiting_items,
    label,
    load_status,
    project_dir,
    read_input,
    run_safely,
)

APPROVAL = re.compile(
    r"^[\s\W]*((yes|yep|ok|okay|great|perfect|thanks|thank\s+you)[\s,.!]+)*"
    r"(/approve\b|(i\s+)?approved?\b|lgtm\b|looks\s+good\b|sign(ed)?[\s-]?off\b"
    r"|go\s+ahead\b|ship\s+it\b|yes,?\s+approved?\b)",
    re.I,
)
# Conditions or open questions make an approval conditional, i.e. not an approval yet.
CONDITIONAL = re.compile(
    r"\b(but|except|however|change|fix|before|instead|tweak|unless|although|wait)\b|\?", re.I
)


def is_explicit_approval(prompt: str) -> bool:
    text = prompt.strip()
    if text.lower().startswith("/approve"):
        note = text[len("/approve") :]
        return not CONDITIONAL.search(note)
    return bool(APPROVAL.search(text)) and not CONDITIONAL.search(text)


def main() -> None:
    hook_input = read_input()
    root = project_dir(hook_input)
    waiting = awaiting_items(load_status(root))
    approved = bool(waiting) and is_explicit_approval(hook_input.get("prompt", ""))

    state = root / STATE_DIR
    state.mkdir(parents=True, exist_ok=True)
    (state / "approval.json").write_text(
        json.dumps(
            {
                "session_id": hook_input.get("session_id"),
                "approved": approved,
                "items": waiting if approved else [],
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        ),
        encoding="utf-8",
    )

    if not waiting:
        return
    items = ", ".join(label(i) for i in waiting)
    if approved:
        add_context(
            "UserPromptSubmit",
            f"[python-waterfall] Awaiting sign-off: {items}. The user's message reads as an "
            "explicit approval. If it clearly approves that item, record it: the "
            "deliverable's header Status → Approved; STATUS.md status → Approved with "
            "today's date and Current phase → the next phase; the user's exact words in "
            "the Sign-off log (a CR: status → Approved). Then continue.",
        )
    add_context(
        "UserPromptSubmit",
        f"[python-waterfall] Awaiting sign-off: {items}. This message is not an "
        "unconditional approval: treat it as feedback or a question, revise if needed, and "
        "ask for approval again. Do not advance the phase. (STATUS.md edits that mark it "
        "approved will be blocked this turn.)",
    )


if __name__ == "__main__":
    run_safely("prompt-signoff", main)
