# Maintenance & Handover — <Project name>

| Version | Date | Release | Status |
|---|---|---|---|
| 1.0 | <YYYY-MM-DD> | v1.0.0 | Draft |

## 1. Runbook

| Task | How |
|---|---|
| Set up | `uv sync --locked` (installs Python per `.python-version` if needed) |
| Run locally | <`uv run <prog> …` / `uv run uvicorn <pkg>.main:app --reload`> |
| Verify | `make check && make test` |
| Build | `make build` |
| Deploy / release | <see 05-deployment.md §5> |
| Roll back | <see 05-deployment.md §7> |

## 2. Known issues & limitations

| Item | Impact | Workaround | Tracking |
|---|---|---|---|
| | | | |

## 3. Accepted defects
<!-- Open defects the user accepted at the P4 gate. -->

## 4. Dependency & security updates
- Cadence: <e.g. monthly `uv lock --upgrade` + `make check test audit`; Dependabot/Renovate for `uv.lock`>
- Major upgrades (incl. a new Python minor): each is a CR with an ADR, followed by full P4 verification.
- Python: move `.python-version` / `requires-python` forward before the current version reaches end-of-life.

## 5. Monitoring
<!-- Error reporting, metrics, uptime — or "None (out of scope per 01-requirements §9)". -->

## 6. Change process
- **Small change / bug:** log CR-### in STATUS.md → update affected docs → implement → test → RTM → release.
- **Major version / new scope:** start a new waterfall cycle at P1, referencing these baselined docs.

## 7. Handover
- Docs index: `docs/waterfall/STATUS.md`
- Contacts / owners: <…>
