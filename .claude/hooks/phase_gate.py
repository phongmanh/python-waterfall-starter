#!/usr/bin/env python3
"""PreToolUse hook: enforces the waterfall gates and basic safety, mechanically.

Phase gates (the user can switch these off with WATERFALL_GATE=off):
  * No application code, project config, scaffolding or installs until P2 Design
    is approved in docs/waterfall/STATUS.md.
  * No CI or deployment config until P4 Testing is approved.
  * Approval guard: an edit to STATUS.md that newly marks a phase or CR as approved
    is allowed only in a turn whose user message was an explicit approval of an
    item that was awaiting it (recorded by prompt_signoff.py).

Always on:
  * Deny commands that would wipe docs/waterfall, read secrets, or force-push.
  * Ask the user before outward-facing commands (push, publish, deploy) and before
    any change to the guardrails themselves (.claude/settings*.json, hooks, agents).
"""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from _waterfall import (
    GUARDRAIL_FILES,
    OVERRIDE_NOTE,
    PHASE_NAMES,
    STATE_DIR,
    STATUS_PATH,
    approved_items,
    describe_phase,
    gate_enabled,
    gates_waived,
    load_status,
    next_phase,
    parse_status,
    phase_approved,
    pretool_decision,
    project_dir,
    read_input,
    relative_to_project,
    required_phase_for,
    run_safely,
)

deny = lambda reason: pretool_decision("deny", reason)  # noqa: E731
ask = lambda reason: pretool_decision("ask", reason)  # noqa: E731


# --- file edits --------------------------------------------------------------


def check_path(root: Path, status: Optional[Dict[str, Any]], rel: str) -> None:
    required = required_phase_for(rel)
    if not required or phase_approved(status, required):
        return
    nxt = next_phase(required)
    deny(
        f"Phase gate: {rel} is Phase {nxt[1:]} ({PHASE_NAMES[nxt]}) work, but "
        f"{describe_phase(status, required)}. Finish the current phase with the "
        f"python-waterfall skill and get the user's explicit approval first. "
        f"{OVERRIDE_NOTE}"
    )


def status_after_edit(path: Path, tool: str, tool_input: Dict[str, Any]) -> Tuple[str, str]:
    """(text before, text after) for an edit to STATUS.md."""
    before = path.read_text(encoding="utf-8") if path.exists() else ""
    if tool == "Write":
        return before, tool_input.get("content", "")
    edits = tool_input.get("edits") if tool == "MultiEdit" else [tool_input]
    after = before
    for e in edits or []:
        old, new = e.get("old_string", ""), e.get("new_string", "")
        after = after.replace(old, new) if e.get("replace_all") else after.replace(old, new, 1)
    return before, after


def load_approval(root: Path) -> Dict[str, Any]:
    try:
        return json.loads((root / STATE_DIR / "approval.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def check_approval_guard(
    root: Path, tool: str, tool_input: Dict[str, Any], hook_input: Dict[str, Any]
) -> None:
    before_text, after_text = status_after_edit(root / STATUS_PATH, tool, tool_input)
    before = parse_status(before_text) if before_text else None
    newly = sorted(set(approved_items(parse_status(after_text))) - set(approved_items(before)))
    if not newly or gates_waived(before):
        return
    approval = load_approval(root)
    same_turn = approval.get("session_id") == hook_input.get("session_id")
    if not (same_turn and approval.get("approved")):
        deny(
            f"Approval guard: this edit marks {', '.join(newly)} as approved, but the "
            "user's latest message is not an explicit approval. Present the deliverable, "
            "ask for sign-off and end your turn. Record the approval only after the "
            "user replies 'approve' (or uses /approve)."
        )
    waiting = set(approval.get("items") or [])
    not_waiting = [i for i in newly if i not in waiting]
    if not_waiting:
        deny(
            f"Approval guard: {', '.join(not_waiting)} was not awaiting approval when "
            f"the user approved (awaiting then: {', '.join(sorted(waiting)) or 'nothing'}). "
            "Only the item the user signed off may be marked approved; anything else "
            "needs its own gate."
        )


def check_edit(root: Path, status: Optional[Dict[str, Any]], hook_input: Dict[str, Any]) -> None:
    tool = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not file_path:
        return
    rel = relative_to_project(root, file_path)
    if rel is None:
        return  # outside the project: not ours to gate
    if GUARDRAIL_FILES.match(rel):
        ask(
            f"{rel} is part of this project's guardrails. Changing it needs the user's "
            "confirmation."
        )
    if not gate_enabled():
        return
    if rel == STATUS_PATH and tool in ("Write", "Edit", "MultiEdit"):
        check_approval_guard(root, tool, tool_input, hook_input)
    check_path(root, status, rel)


# --- shell commands ----------------------------------------------------------

SEGMENT_OPS = {";", "&&", "||", "|", "&", "(", ")", "|&", ";;", "\n"}
REDIRECT_OPS = {">", ">>", ">|", "&>", "&>>", ">&"}
WRITE_CMDS = {"cp", "mv", "tee", "touch", "mkdir", "ln", "install", "rsync", "truncate", "dd"}
READ_CMDS = {
    "cat", "less", "more", "head", "tail", "bat", "strings", "base64", "xxd", "od",
    "hexdump", "cp", "scp", "rsync", "curl", "nl", "awk", "sed", "grep", "rg", "open",
}  # fmt: skip
PREFIX_CMDS = {"sudo", "env", "command", "exec", "nohup", "time", "xargs"}
WRAPPER_VALUE_FLAGS = {"-u", "-g", "-C", "-D", "-h", "-p", "-U", "-n", "-I"}
SHELLS = {"sh", "bash", "zsh", "dash"}

SECRET_FILE = re.compile(
    r"(^|/)(\.env(\.(?!example$|sample$|template$)[\w.-]+)?|.*\.pem|.*\.key|id_(rsa|dsa|ecdsa|ed25519)"
    r"|credentials\.json|service[-_]account[\w.-]*\.json|\.pypirc|\.netrc|\.git-credentials)$"
)


HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_]\w*)\1")


def normalize(command: str) -> str:
    """Drop heredoc bodies (data, not commands) and turn unquoted newlines into `;`."""
    lines, out, delim = command.replace("\\\n", " ").split("\n"), [], None
    skipped: List[str] = []
    for line in lines:
        if delim is not None:
            skipped.append(line)
            if line.strip() == delim:
                delim, skipped = None, []
            continue
        out.append(line)
        m = HEREDOC.search(line.replace("<<<", "   "))
        if m:
            delim = m.group(2)
    out += skipped  # unterminated "heredoc" (e.g. `<<` inside quotes): keep the lines
    text, result, quote = "\n".join(out), [], ""
    for ch in text:
        if quote:
            quote = "" if ch == quote else quote
        elif ch in "'\"":
            quote = ch
        elif ch == "\n":
            ch = " ; "
        result.append(ch)
    return "".join(result)


def tokenize(command: str) -> Tuple[List[List[str]], List[str]]:
    """Split a shell command into simple-command segments and redirect targets."""
    lexer = shlex.shlex(normalize(command), posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    segments: List[List[str]] = [[]]
    targets: List[str] = []
    tokens = list(lexer)
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in SEGMENT_OPS:
            segments.append([])
        elif tok in REDIRECT_OPS or re.fullmatch(r"[<>&|]*>[<>&|]*", tok):
            if i + 1 < len(tokens) and not re.fullmatch(r"\d+|-", tokens[i + 1]):
                targets.append(tokens[i + 1])
            i += 1
        elif tok.startswith("<"):
            i += 1 if tok in ("<", "<<", "<<<") else 0  # skip the input operand
        else:
            segments[-1].append(tok)
        i += 1
    result: List[List[str]] = []
    for seg in (strip_prefix(s) for s in segments):
        if not seg:
            continue
        result.append(seg)
        if seg[0] in SHELLS and "-c" in seg[:-1]:  # inspect `bash -c "…"` too
            inner_segments, inner_targets = tokenize(seg[seg.index("-c") + 1])
            result += inner_segments
            targets += inner_targets
    return result, targets


def strip_prefix(seg: List[str]) -> List[str]:
    """Drop VAR=value assignments and wrappers like sudo/env so seg[0] is the program."""
    i, in_wrapper = 0, False
    while i < len(seg):
        if re.fullmatch(r"[A-Za-z_]\w*=.*", seg[i]) or seg[i] in PREFIX_CMDS:
            in_wrapper = in_wrapper or seg[i] in PREFIX_CMDS
            i += 1
        elif in_wrapper and seg[i].startswith("-"):
            # wrapper options, e.g. `env -i`, `sudo -u bob` (skip the option's value too)
            i += 2 if seg[i] in WRAPPER_VALUE_FLAGS else 1
        else:
            break
    out = seg[i:]
    if out:
        out[0] = out[0].rsplit("/", 1)[-1]
    return out


def args(seg: List[str]) -> List[str]:
    return [a for a in seg[1:] if not a.startswith("-")]


def has_flag(seg: List[str], *flags: str) -> bool:
    for a in seg[1:]:
        if a in flags:
            return True
        short = [f[1] for f in flags if len(f) == 2 and f[0] == "-"]
        if re.fullmatch(r"-[A-Za-z]+", a) and any(c in a[1:] for c in short):
            return True
    return False


def sub(seg: List[str]) -> str:
    """The subcommand(s) after the program, e.g. 'pip install' for `uv pip install x`."""
    return " ".join(args(seg)[:2])


SCAFFOLD = [
    ("uv", re.compile(r"^(init|add|remove|sync|lock|venv|pip (install|sync|compile))\b")),
    ("pip", re.compile(r"^(install|download)\b")),
    ("pip3", re.compile(r"^(install|download)\b")),
    ("poetry", re.compile(r"^(new|init|add|install|lock)\b")),
    ("pdm", re.compile(r"^(init|add|install|lock)\b")),
    ("hatch", re.compile(r"^new\b")),
    ("pipenv", re.compile(r"^install\b")),
    ("conda", re.compile(r"^(create|install)\b")),
    ("mamba", re.compile(r"^(create|install)\b")),
    ("virtualenv", re.compile(r"")),
    ("cookiecutter", re.compile(r"")),
    ("copier", re.compile(r"")),
    ("django-admin", re.compile(r"^startproject\b")),
]

OUTWARD = [
    ("git", re.compile(r"^push\b")),
    ("gh", re.compile(r"^(repo create|release create|secret set|variable set|pr create|pr merge|workflow run)\b")),
    ("uv", re.compile(r"^publish\b")),
    ("twine", re.compile(r"^upload\b")),
    ("poetry", re.compile(r"^publish\b")),
    ("hatch", re.compile(r"^publish\b")),
    ("pdm", re.compile(r"^publish\b")),
    ("flit", re.compile(r"^publish\b")),
    ("docker", re.compile(r"^push\b")),
    ("fly", re.compile(r"^deploy\b")),
    ("flyctl", re.compile(r"^deploy\b")),
    ("vercel", re.compile(r"")),
    ("railway", re.compile(r"^up\b")),
    ("heroku", re.compile(r"")),
    ("kubectl", re.compile(r"^(apply|delete|rollout|scale|set)\b")),
    ("helm", re.compile(r"^(install|upgrade|uninstall|rollback)\b")),
    ("terraform", re.compile(r"^(apply|destroy|import)\b")),
    ("gcloud", re.compile(r".*\bdeploy\b")),
    ("aws", re.compile(r".*\b(deploy|update-function-code)\b")),
]  # fmt: skip


def matches(table: List[Tuple[str, "re.Pattern[str]"]], seg: List[str]) -> bool:
    return any(seg[0] == prog and rx.search(sub(seg)) for prog, rx in table)


def is_pip_module(seg: List[str]) -> bool:
    """`python -m pip install`, `python3.14 -m venv .venv`, …"""
    if not re.fullmatch(r"python[\d.]*", seg[0]) or "-m" not in seg:
        return False
    rest = seg[seg.index("-m") + 1 :]
    return bool(rest) and (
        rest[0] in ("venv", "virtualenv")
        or (rest[0] in ("pip", "pip3") and len(rest) > 1 and rest[1] in ("install", "download"))
    )


def write_targets(seg: List[str]) -> Iterator[str]:
    prog = seg[0]
    if prog in ("cp", "ln", "install", "rsync", "scp") and args(seg):
        yield args(seg)[-1]  # the destination; sources are only read
    elif prog in WRITE_CMDS:
        yield from args(seg)
    elif prog in ("sed", "perl") and any(re.fullmatch(r"-\w*i\w*", a) for a in seg[1:]):
        yield from args(seg)[1:]  # skip the script


def check_bash(root: Path, status: Optional[Dict[str, Any]], command: str) -> None:
    try:
        segments, redirects = tokenize(command)
    except ValueError:
        segments, redirects = [command.split()], []  # unbalanced quotes: best effort

    for seg in segments:
        prog = seg[0]
        if prog == "rm":
            recursive = has_flag(seg, "-r", "-R", "--recursive")
            for a in args(seg):
                rel = relative_to_project(root, a)
                if (
                    (recursive and a in ("*", "~", "~/", "/", "/*"))
                    or rel in (".", "docs", "docs/*")
                    or (rel or "").startswith("docs/waterfall")
                ):
                    deny(f"Blocked: `{' '.join(seg)}` would delete the baselined waterfall documents.")
        if prog == "git" and sub(seg).startswith("clean") and has_flag(seg, "-f", "--force"):
            deny("Blocked: `git clean -f` can delete uncommitted docs/waterfall files. Ask the user to run it.")
        if prog == "git" and sub(seg).startswith("push") and (
            has_flag(seg, "-f", "--force", "--force-with-lease", "--force-if-includes", "--mirror")
            or any(a.startswith("+") for a in args(seg))
        ):
            deny("Blocked: force-pushing rewrites shared history. Ask the user to do it if it is really needed.")
        sources = args(seg)[:-1] if prog in ("cp", "mv", "rsync", "scp") else args(seg)
        if prog in READ_CMDS and any(SECRET_FILE.search(a) for a in sources):
            deny("Blocked: this command reads or copies a secrets file. Ask the user to handle it (see .claude/rules/security.md).")

    targets = redirects + [t for seg in segments for t in write_targets(seg)]
    rels = [r for r in (relative_to_project(root, t) for t in targets) if r]

    if any(r == STATUS_PATH for r in rels) and gate_enabled():
        deny(f"Edit {STATUS_PATH} with the Edit tool, not the shell, so the approval guard can check it.")
    guarded = [r for r in rels if GUARDRAIL_FILES.match(r)]

    if gate_enabled():
        for seg in segments:
            if (matches(SCAFFOLD, seg) or is_pip_module(seg)) and not phase_approved(status, "P2"):
                deny(
                    "Phase gate: scaffolding and installing dependencies are Phase 3 work, "
                    f"but {describe_phase(status, 'P2')}. {OVERRIDE_NOTE}"
                )
        for rel in rels:
            check_path(root, status, rel)

    if guarded:
        ask(f"This command changes the project's guardrails ({', '.join(guarded)}). Confirm it.")
    for seg in segments:
        if matches(OUTWARD, seg) or (seg[0] == "docker" and "--push" in seg):
            ask(f"Outward-facing action: `{' '.join(seg)}` publishes, pushes or deploys. Confirm you want to run exactly this.")
        if seg[0] == "git" and sub(seg).startswith("reset") and "--hard" in seg:
            ask("`git reset --hard` discards uncommitted work, including unsaved phase documents. Confirm it.")


def main() -> None:
    hook_input = read_input()
    root = project_dir(hook_input)
    status = load_status(root)
    tool = hook_input.get("tool_name", "")
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        check_edit(root, status, hook_input)
    elif tool == "Bash":
        command = (hook_input.get("tool_input") or {}).get("command", "")
        if command:
            check_bash(root, status, command)


if __name__ == "__main__":
    run_safely("phase-gate", main)
