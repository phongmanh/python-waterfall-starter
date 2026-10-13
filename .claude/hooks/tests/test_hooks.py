"""Tests for the waterfall hooks. Each hook runs as a subprocess with JSON on stdin,
exactly as Claude Code runs it. Standard library only:

    python3 -m unittest discover -s .claude/hooks/tests -v
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, Optional

HOOKS = Path(__file__).resolve().parents[1]
TEMPLATE = HOOKS.parent / "skills" / "python-waterfall" / "assets" / "templates" / "STATUS.md"
SESSION = "session-1"


def status_text(phases: Optional[Dict[str, str]] = None, gate_policy: str = "", crs: str = "") -> str:
    """The real STATUS.md template with phase statuses (and CR rows) filled in."""
    text = TEMPLATE.read_text(encoding="utf-8")
    for pid, value in (phases or {}).items():
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith(f"| {pid} "):
                cells = line.split("|")
                cells[3] = f" {value} "
                if value.startswith("Approved"):
                    cells[4] = " 2026-10-13 "
                lines[i] = "|".join(cells)
        text = "\n".join(lines) + "\n"
    if gate_policy:
        text = text.replace("| Gate policy | Hard sign-off per phase", f"| Gate policy | {gate_policy}")
    if crs:
        text = text.replace("| ID | Date | Change & reason | Affects (docs / files / tests) | Status |\n|---|---|---|---|---|\n",
                            "| ID | Date | Change & reason | Affects (docs / files / tests) | Status |\n|---|---|---|---|---|\n" + crs)
    return text


class HookTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.env = {k: v for k, v in os.environ.items() if k != "WATERFALL_GATE"}
        self.env["CLAUDE_PROJECT_DIR"] = str(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write_status(self, **kwargs: Any) -> Path:
        path = self.root / "docs" / "waterfall" / "STATUS.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(status_text(**kwargs), encoding="utf-8")
        return path

    def run_hook(self, name: str, payload: Dict[str, Any], **env: str) -> subprocess.CompletedProcess:
        payload.setdefault("session_id", SESSION)
        payload.setdefault("cwd", str(self.root))
        return subprocess.run(
            [sys.executable, str(HOOKS / name)],
            input=json.dumps(payload), capture_output=True, text=True,
            env={**self.env, **env}, timeout=30, check=False,
        )

    def decision(self, proc: subprocess.CompletedProcess) -> str:
        self.assertEqual(proc.returncode, 0, proc.stderr)
        if not proc.stdout.strip():
            return "allow"
        return json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"]

    def gate(self, tool: str, tool_input: Dict[str, Any], **env: str) -> str:
        return self.decision(self.run_hook("phase_gate.py", {"tool_name": tool, "tool_input": tool_input}, **env))

    def bash(self, command: str, **env: str) -> str:
        return self.gate("Bash", {"command": command}, **env)

    def write(self, rel: str, **env: str) -> str:
        return self.gate("Write", {"file_path": str(self.root / rel), "content": "x"}, **env)


class PhaseGateFileTests(HookTestCase):
    def test_app_code_blocked_without_a_project(self) -> None:
        self.assertEqual(self.write("src/app/main.py"), "deny")

    def test_docs_always_allowed(self) -> None:
        self.assertEqual(self.write("docs/waterfall/01-requirements.md"), "allow")

    def test_app_code_and_config_blocked_until_design_approved(self) -> None:
        self.write_status(phases={"P1": "Approved", "P2": "In progress"})
        for rel in ("src/app/main.py", "tests/test_x.py", "pyproject.toml", "uv.lock",
                    ".python-version", "Makefile", "tool.py", "notebooks/explore.ipynb"):
            self.assertEqual(self.write(rel), "deny", rel)

    def test_app_code_allowed_once_design_approved(self) -> None:
        self.write_status(phases={"P1": "Approved", "P2": "Approved", "P3": "In progress"})
        self.assertEqual(self.write("src/app/main.py"), "allow")
        self.assertEqual(self.write("pyproject.toml"), "allow")
        self.assertEqual(self.write("README.md"), "allow")

    def test_deploy_config_needs_testing_approved(self) -> None:
        self.write_status(phases={"P1": "Approved", "P2": "Approved", "P3": "Approved"})
        for rel in (".github/workflows/ci.yml", "Dockerfile", "compose.yaml", "deploy/k8s.yaml"):
            self.assertEqual(self.write(rel), "deny", rel)
        self.write_status(phases={p: "Approved" for p in ("P1", "P2", "P3", "P4")})
        self.assertEqual(self.write("Dockerfile"), "allow")

    def test_hooks_ci_workflow_is_not_gated(self) -> None:
        self.assertEqual(self.write(".github/workflows/claude-hooks.yml"), "allow")

    def test_gate_off_allows_app_code(self) -> None:
        self.assertEqual(self.write("src/app/main.py", WATERFALL_GATE="off"), "allow")

    def test_guardrail_edits_ask(self) -> None:
        for rel in (".claude/settings.json", ".claude/settings.local.json", ".claude/hooks/phase_gate.py"):
            self.assertEqual(self.write(rel), "ask", rel)
        self.assertEqual(self.write(".claude/rules/python.md"), "allow")

    def test_outside_project_is_ignored(self) -> None:
        self.assertEqual(self.gate("Write", {"file_path": "/tmp/elsewhere/x.py", "content": ""}), "allow")


class ApprovalGuardTests(HookTestCase):
    def edit_p1_to_approved(self) -> str:
        path = self.root / "docs" / "waterfall" / "STATUS.md"
        line = next(ln for ln in path.read_text().splitlines() if ln.startswith("| P1 "))
        new = line.replace("Awaiting approval", "Approved")
        return self.gate("Edit", {"file_path": str(path), "old_string": line, "new_string": new})

    def approval(self, approved: bool, items: list, session: str = SESSION) -> None:
        state = self.root / ".claude" / "state"
        state.mkdir(parents=True, exist_ok=True)
        (state / "approval.json").write_text(json.dumps({"session_id": session, "approved": approved, "items": items}))

    def test_blocks_self_approval(self) -> None:
        self.write_status(phases={"P1": "Awaiting approval"})
        self.assertEqual(self.edit_p1_to_approved(), "deny")
        self.approval(False, [])
        self.assertEqual(self.edit_p1_to_approved(), "deny")

    def test_allows_after_explicit_approval(self) -> None:
        self.write_status(phases={"P1": "Awaiting approval"})
        self.approval(True, ["P1"])
        self.assertEqual(self.edit_p1_to_approved(), "allow")

    def test_approval_from_another_session_does_not_count(self) -> None:
        self.write_status(phases={"P1": "Awaiting approval"})
        self.approval(True, ["P1"], session="other")
        self.assertEqual(self.edit_p1_to_approved(), "deny")

    def test_only_the_awaiting_item_may_be_approved(self) -> None:
        self.write_status(phases={"P1": "Awaiting approval"})
        self.approval(True, ["CR-001"])
        self.assertEqual(self.edit_p1_to_approved(), "deny")

    def test_waived_gates_allow(self) -> None:
        self.write_status(phases={"P1": "Awaiting approval"}, gate_policy="Gates waived by user on 2026-10-13: 'no stops'")
        self.assertEqual(self.edit_p1_to_approved(), "allow")

    def test_new_cr_row_cannot_start_approved(self) -> None:
        path = self.write_status(phases={"P1": "Approved"})
        content = path.read_text().replace(
            "|---|---|---|---|---|\n| | | | | |", "|---|---|---|---|---|\n| CR-001 | 2026-10-13 | add x | FR-001 | Approved |")
        self.assertEqual(self.gate("Write", {"file_path": str(path), "content": content}), "deny")

    def test_other_status_edits_allowed(self) -> None:
        path = self.write_status(phases={"P1": "In progress"})
        line = next(ln for ln in path.read_text().splitlines() if ln.startswith("| P1 "))
        self.assertEqual(self.gate("Edit", {"file_path": str(path), "old_string": line,
                                            "new_string": line.replace("In progress", "Awaiting approval")}), "allow")

    def test_shell_writes_to_status_blocked(self) -> None:
        self.assertEqual(self.bash("sed -i '' 's/Awaiting approval/Approved/' docs/waterfall/STATUS.md"), "deny")
        self.assertEqual(self.bash("cat docs/waterfall/STATUS.md"), "allow")


class PhaseGateBashTests(HookTestCase):
    def test_installs_blocked_until_design_approved(self) -> None:
        for cmd in ("uv add fastapi", "uv init --package .", "uv pip install requests", "pip install x",
                    "python3 -m pip install x", "python3.14 -m venv .venv", "poetry add x",
                    "cd /tmp && uv sync", "FOO=1 uv add --dev ruff"):
            self.assertEqual(self.bash(cmd), "deny", cmd)
        self.write_status(phases={"P1": "Approved", "P2": "Approved"})
        self.assertEqual(self.bash("uv add fastapi"), "allow")

    def test_harmless_commands_allowed_before_design(self) -> None:
        for cmd in ("uv --version", "uv run python -V", "uv tool install ruff", "ls -la", "git status",
                    "python3 -m unittest discover -s .claude/hooks/tests 2>&1 | tail -5",
                    "cat > /tmp/notes.txt <<'EOF'\nsrc/app/main.py\nrm -rf docs\nEOF",
                    'git commit -m "docs: P1\n\nmentions rm -rf docs in the body"'):
            self.assertEqual(self.bash(cmd), "allow", cmd)

    def test_shell_writes_to_app_paths_blocked_until_design(self) -> None:
        for cmd in ("echo 'x' > src/app.py", "mkdir -p src/app", "mkdir src", "touch pyproject.toml",
                    "cp /tmp/a.py tests/test_a.py", "printf x | tee tests/a.py"):
            self.assertEqual(self.bash(cmd), "deny", cmd)

    def test_destroying_docs_always_blocked(self) -> None:
        for cmd in ("rm -rf docs", "rm -rf ./docs/", "rm docs/waterfall/01-requirements.md", "rm -rf .",
                    "rm -fr *", "echo hi\nrm -rf docs", "git clean -fdx", "bash -c 'rm -rf docs'",
                    "echo '<<X'\nrm -rf docs", "sudo -u me rm -rf ./docs"):
            self.assertEqual(self.bash(cmd, WATERFALL_GATE="off"), "deny", cmd)
        self.assertEqual(self.bash("rm -rf build dist .pytest_cache"), "allow")

    def test_secrets_never_read(self) -> None:
        for cmd in ("cat .env", "grep KEY .env.local", "head -1 config/prod.pem", "cp ~/.pypirc /tmp/x"):
            self.assertEqual(self.bash(cmd), "deny", cmd)
        self.assertEqual(self.bash("cp .env.example .env"), "allow")
        self.assertEqual(self.bash("cat .env.example"), "allow")

    def test_force_push_denied_and_push_asks(self) -> None:
        for cmd in ("git push --force origin main", "git push -f", "git push origin +main", "git push --force-with-lease"):
            self.assertEqual(self.bash(cmd), "deny", cmd)
        for cmd in ("git push origin main", "git add -A && git commit -m x && git push", "uv publish",
                    "gh pr create --fill", "docker buildx build --push -t x .", "twine upload dist/*"):
            self.assertEqual(self.bash(cmd), "ask", cmd)

    def test_reset_hard_asks(self) -> None:
        self.assertEqual(self.bash("git reset --hard HEAD~1"), "ask")

    def test_shell_writes_to_guardrails_ask(self) -> None:
        self.assertEqual(self.bash("echo '{}' > .claude/settings.json"), "ask")


class SessionContextTests(HookTestCase):
    def context(self) -> str:
        proc = self.run_hook("session_context.py", {"hook_event_name": "SessionStart", "source": "startup"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]

    def test_no_project(self) -> None:
        self.assertIn("no project started yet", self.context())

    def test_reports_phases_and_pending_signoff(self) -> None:
        self.write_status(phases={"P1": "Approved", "P2": "Awaiting approval"},
                          crs="| CR-001 | 2026-10-13 | rename | FR-001 | Proposed |\n")
        ctx = self.context()
        self.assertIn("P1 Requirements: Approved (approved 2026-10-13)", ctx)
        self.assertIn("Awaiting the user's sign-off: P2 Design, CR-001", ctx)
        self.assertIn("Open change requests: CR-001 (Proposed)", ctx)


class PromptSignoffTests(HookTestCase):
    def submit(self, prompt: str) -> Dict[str, Any]:
        proc = self.run_hook("prompt_signoff.py", {"hook_event_name": "UserPromptSubmit", "prompt": prompt})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        state = json.loads((self.root / ".claude" / "state" / "approval.json").read_text())
        ctx = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"] if proc.stdout.strip() else ""
        return {"approved": state["approved"], "items": state["items"], "context": ctx}

    def test_explicit_approvals(self) -> None:
        self.write_status(phases={"P1": "Awaiting approval"})
        for prompt in ("approve", "Approved.", "LGTM", "looks good, go ahead", "/approve", "ok, approve",
                       "/approve thanks"):
            result = self.submit(prompt)
            self.assertTrue(result["approved"], prompt)
            self.assertEqual(result["items"], ["P1"])
            self.assertIn("explicit approval", result["context"])

    def test_conditional_or_unrelated_messages_are_not_approvals(self) -> None:
        self.write_status(phases={"P1": "Awaiting approval"})
        for prompt in ("approve but change FR-002", "looks good?", "what about offline mode",
                       "/approve after you fix the typo", "I don't approve", "go ahead and change the title"):
            result = self.submit(prompt)
            self.assertFalse(result["approved"], prompt)
            self.assertIn("not an unconditional approval", result["context"])

    def test_nothing_awaiting(self) -> None:
        self.write_status(phases={"P1": "In progress"})
        result = self.submit("approve")
        self.assertFalse(result["approved"])
        self.assertEqual(result["context"], "")


def fake_tool(root: Path, name: str, script: str) -> None:
    path = root / ".venv" / "bin" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + script + "\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@unittest.skipIf(sys.platform == "win32", "fake tools are POSIX shell scripts")
class FormatLintTests(HookTestCase):
    def post(self, rel: str) -> subprocess.CompletedProcess:
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x = 1\n")
        return self.run_hook("format_lint.py", {"tool_name": "Write", "tool_input": {"file_path": str(target)}})

    def test_inactive_without_environment(self) -> None:
        self.assertEqual(self.post("src/app/main.py").returncode, 0)

    def test_lint_errors_go_back_to_claude(self) -> None:
        fake_tool(self.root, "ruff", 'if [ "$1" = check ]; then echo "src/app/main.py:1:1: F401 unused"; exit 1; fi')
        proc = self.post("src/app/main.py")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("F401", proc.stderr)

    def test_clean_file_passes_and_non_python_is_skipped(self) -> None:
        fake_tool(self.root, "ruff", "exit 0")
        self.assertEqual(self.post("src/app/main.py").returncode, 0)
        fake_tool(self.root, "ruff", "exit 1")
        self.assertEqual(self.post("docs/waterfall/notes.py").returncode, 0)
        self.assertEqual(self.post("README.md").returncode, 0)


@unittest.skipIf(sys.platform == "win32", "fake tools are POSIX shell scripts")
class QualityGateTests(HookTestCase):
    def stop(self, **extra: Any) -> subprocess.CompletedProcess:
        return self.run_hook("quality_gate.py", {"hook_event_name": "Stop", **extra})

    def setUp(self) -> None:
        super().setUp()
        (self.root / "src" / "app").mkdir(parents=True)
        (self.root / "src" / "app" / "__init__.py").write_text("")
        fake_tool(self.root, "ruff", "exit 0")

    def test_failing_mypy_blocks_stop(self) -> None:
        fake_tool(self.root, "mypy", 'echo "src/app/__init__.py:1: error: bad"; exit 1')
        proc = self.stop()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("mypy failed", proc.stderr)

    def test_does_not_loop(self) -> None:
        fake_tool(self.root, "mypy", "exit 1")
        self.assertEqual(self.stop(stop_hook_active=True).returncode, 0)

    def test_green_run_is_stamped_and_skipped_until_code_changes(self) -> None:
        fake_tool(self.root, "mypy", "exit 0")
        self.assertEqual(self.stop().returncode, 0)
        fake_tool(self.root, "mypy", "exit 1")
        self.assertEqual(self.stop().returncode, 0)  # nothing changed since the green stamp
        time.sleep(0.01)
        later = time.time() + 2
        os.utime(self.root / "src" / "app" / "__init__.py", (later, later))
        self.assertEqual(self.stop().returncode, 2)


if __name__ == "__main__":
    unittest.main()
