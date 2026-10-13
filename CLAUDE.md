# Python Waterfall Starter

This repo is an empty starting point for building Python software (a CLI, web API, library or worker) with the **Waterfall** SDLC. The software doesn't exist yet. It gets specified, designed, built, tested and shipped here, one approved phase at a time.

## How work happens here

- **Use the `python-waterfall` skill** (`.claude/skills/python-waterfall/`) for all project work, from the first requirement to the final handover.
- **This repository root is the project root.** Write docs to `docs/waterfall/` and scaffold the package into the root itself (`uv init … .`), not into a subfolder. The skill's tech-stack setup scaffolds next to the existing files without overwriting them.
- **`docs/waterfall/STATUS.md` says where things stand.** The SessionStart hook summarises it at the start of every session. `/waterfall-status` shows the detail.
- **Process and security rules** are in `.claude/rules/waterfall-process.md` and `.claude/rules/security.md` (always loaded). Python, testing, dependency and phase-doc rules load automatically when matching files are touched.

## Slash commands

| Command | Use |
|---|---|
| `/waterfall-status` | Current phase, sign-offs, open change requests, next action |
| `/approve [note]` | Sign off the phase or CR that's awaiting approval |
| `/change-request <what and why>` | Open a CR against baselined docs, with impact analysis |

## Enforced by hooks (`.claude/settings.json` → `.claude/hooks/`, stdlib Python)

| Hook | Event | Does |
|---|---|---|
| `session_context.py` | SessionStart | Injects the phase status from STATUS.md |
| `prompt_signoff.py` | UserPromptSubmit | When something awaits sign-off, tells Claude whether the message is an explicit approval, and records the verdict for the approval guard |
| `phase_gate.py` | PreToolUse | Blocks app code, project config, `uv init`/`uv add`/`pip install` until **P2 Design** is approved, and CI/deploy config until **P4 Testing** is approved. Blocks marking anything approved in STATUS.md unless the user approved it this turn. Always blocks wiping `docs/waterfall/`, reading secrets and force-pushes. Asks before push/publish/deploy and before changes to the guardrails. |
| `format_lint.py` | PostToolUse | After an edit to a `.py` file: `ruff check --fix`, then `ruff format`. Remaining errors go back to Claude. Inactive until `.venv` exists. |
| `quality_gate.py` | Stop | Won't end a turn while changed code fails ruff or mypy. Inactive until `.venv` exists. |

A blocked tool call means: finish the phase, or ask the user. Only the user can disable the phase gates, with `"env": { "WATERFALL_GATE": "off" }` in `.claude/settings.local.json`. The safety checks stay on. Hook tests: `python3 -m unittest discover -s .claude/hooks/tests`.

## Commands (available from Phase 3 on, once the project is scaffolded)

- `make check`: format check + lint + mypy --strict + fast tests (the per-module gate)
- `make test` / `make coverage` / `make rtm`: all tests, with branch coverage, and requirement → test traceability
- `make audit` / `make build`: dependency vulnerability scan, and sdist + wheel
- Run anything in the project environment with `uv run …`. Add dependencies with `uv add` (design-approved only).

Requires [uv](https://docs.astral.sh/uv/). It installs the Python version pinned in `.python-version`.

## Git

- Use Conventional Commits that cite IDs, e.g. `feat(cli): add expense command (FR-002)` or `docs(waterfall): approve P1 requirements`.
- Commit only once the user has agreed a commit policy for this project; it's recorded in STATUS.md. Never push, publish, deploy or create remote resources without asking. Force-push is denied.
- Never commit secrets. `.env` files are git-ignored and unreadable by Claude.
