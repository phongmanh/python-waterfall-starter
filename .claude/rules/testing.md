---
paths:
  - "tests/**"
---

# Testing rules

Full guide: `.claude/skills/python-waterfall/references/testing.md`. The non-negotiables:

- **Every test carries the requirement IDs it verifies:** `@pytest.mark.req("AC-003.2")` (or a module-level `pytestmark`). Defect regression tests add the `DEF-###`. `make rtm` builds the RTM from these markers, and malformed IDs fail collection.
- Test behaviour through public interfaces: CLI output + exit code, HTTP status + body, return values and raised exceptions. Don't test private helpers or call order.
- One behaviour per test, Arrange–Act–Assert, plain `assert`. Use `pytest.raises(..., match=...)` for errors and `parametrize` with `ids=` for case tables.
- Prefer in-memory fakes of the ports over mocks. If you must mock, use `autospec`. Never call real third-party services. Unit tests have no I/O, no real clock and no unseeded randomness. Never `sleep`.
- Use hypothesis for parsers, round-trips and invariants.
- Integration tests (`tests/integration/`) use real adapters. E2E tests (`tests/e2e/`) run the real entry point (subprocess for CLIs, `TestClient` for APIs). Both are auto-marked and excluded from `make check`, so run `make test` before a gate.
- Warnings are errors. Fix the cause, or add a targeted `filterwarnings` ignore with a comment.
- Tests are typed and linted like production code.
