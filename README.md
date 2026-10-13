# Python Waterfall Starter

An empty project, set up so that [Claude Code](https://claude.com/claude-code) builds **Python software** (a CLI tool, web API, library or worker) with the **Waterfall** method. The software is specified, designed, built, tested and shipped one approved phase at a time, using best-practice defaults.

```
P1 Requirements ─▶ P2 Design ─▶ P3 Implementation ─▶ P4 Testing ─▶ P5 Deployment ─▶ P6 Maintenance
   SRS               SDD + ADRs    code + log           test report    CI + release     runbook
       ▲ you approve      ▲ you approve     ▲ you approve      ▲ you approve    ▲ you approve
```

Every phase produces a document in `docs/waterfall/` and waits for your explicit sign-off. Changes to approved work go through logged change requests. Every requirement is traced through design and code to a passing test (`@pytest.mark.req("AC-001.1")` → `make rtm`).

## Quick start

Prerequisites: [Claude Code](https://claude.com/claude-code), [uv](https://docs.astral.sh/uv/getting-started/installation/), and `python3` on your PATH (any version from 3.9 up; it runs the hooks).

```bash
git clone git@github.com:phongmanh/python-waterfall-starter.git my-project
cd my-project
claude
```

Then describe what you want, for example:

> Build a CLI that imports my bank CSV exports and reports monthly spending, using the waterfall process.

Claude interviews you, writes `docs/waterfall/01-requirements.md`, and stops for your approval. Reply **approve** (or type `/approve`) to move on, or tell it what to change.

## What's inside

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Project instructions loaded into every Claude session |
| `.claude/skills/python-waterfall/` | The skill: the phase workflow, coding standard, stack profiles and setup, testing guide, templates for each phase's document, and the scaffold files (`pyproject` tool config, `Makefile`, traceability `conftest.py`, pre-commit, CI, Dockerfile) |
| `.claude/skills/{waterfall-status,approve,change-request}/` | Slash commands `/waterfall-status`, `/approve`, `/change-request` |
| `.claude/rules/` | Process and security rules (always loaded), plus Python, testing, dependency and phase-doc rules that load when matching files are touched |
| `.claude/agents/phase-reviewer.md` | A read-only reviewer that checks each deliverable against its exit criteria before you are asked to sign off |
| `.claude/hooks/` | Stdlib-only Python hooks that enforce the gates (see below), with tests |
| `.claude/settings.json` | Hook wiring and permissions. `make`, `uv run` and git commits run without prompts. Push, publish and deploy always ask. Force-push and reading secrets are denied. |
| `.github/` | PR template and CI for the hooks. The project's own CI is added in Phase 5. |

## Guardrails

| | |
|---|---|
| **Phase gate** | No application code, `pyproject.toml`, `uv init`, `uv add` or `pip install` until the Design phase is approved. No CI or deploy config until Testing is approved. |
| **Approval guard** | Claude can't mark a phase or CR as approved in STATUS.md unless your message in that turn was an explicit, unconditional approval of exactly that item. |
| **Doc protection** | Blocks `rm` of `docs/waterfall/`, `rm -rf .`, and `git clean -f`, which would wipe the baselined documents. |
| **Secrets** | Blocks reading `.env`, keys and credential files, through both tools and the shell. |
| **Outward actions** | `git push`, `uv publish`, `docker push`, deploys and `gh pr create` always ask first. Force-push is denied. |
| **Auto-format + lint** | Once the project has a `.venv`, every Python file Claude edits is formatted and linted with ruff. Errors go straight back to Claude. |
| **Quality gate** | Claude can't end a turn while changed code fails ruff or `mypy --strict`. |
| **Session context** | Each session starts with the current phase status, so work resumes exactly where it stopped. |

To bypass the phase gates yourself (for example, for a spike), add this to `.claude/settings.local.json`, which is git-ignored. The safety checks stay on.

```json
{ "env": { "WATERFALL_GATE": "off" } }
```

## Default stack

uv (project, lock, build, audit) · CPython 3.14 · src layout · ruff · mypy --strict · pytest 9 + pytest-cov + hypothesis · pre-commit · Pydantic v2 / pydantic-settings at the boundaries. Profiles add **Typer** for CLIs, **FastAPI + SQLAlchemy 2 + Alembic** (tested with `httpx2`) for APIs, and **structlog** for services. Details and alternatives: `.claude/skills/python-waterfall/references/tech-stack.md`. If a requirement calls for a different choice, the Design phase records it as an ADR.

## Developing the tooling

```bash
python3 -m unittest discover -s .claude/hooks/tests -v
```
