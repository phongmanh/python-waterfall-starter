# Implementation Log — <Project name>

Implements: 02-design.md v<x>

## Environment

| Item | Value |
|---|---|
| Python | <`uv run python --version`> (`.python-version`: <x.y>) |
| uv | <`uv --version`> |
| Resolved versions | <from `uv tree --depth 1`: ruff x, mypy x, pytest x, hypothesis x, + runtime deps> |
| Setup deviations from tech-stack.md | <none / what changed and why> |

## Module progress
<!-- One row per build-order module, appended as each completes. "check" = `make check` result. -->

| # | Module | FRs | Files | Tests | check | Notes / deviations |
|---|---|---|---|---|---|---|
| 1 | Foundation | — | `pyproject.toml`, `Makefile`, `src/<pkg>/__init__.py`, `tests/conftest.py` | — | ✅ | |

## FR → files

| FR | Implementing files |
|---|---|
| FR-001 | |

## Decisions made within the design's latitude
<!-- Internal details the design left open (private helpers, internal module splits). Anything visible in the design doc needs a CR instead. -->
-

## Lint/type exceptions
<!-- Every `# noqa: CODE`, `# type: ignore[code]`, `cast()` or per-file ignore, with file and reason. Target: none. -->

| File:line | Exception | Reason |
|---|---|---|

## Final state
- `make check`: <result>
- `make test`: <n passed>
- `make build`: <artifacts>
