# Testing & verification

Contents: 1. Strategy · 2. Writing tests · 3. Fakes, mocks & external dependencies · 4. Integration & e2e · 5. NFR verification · 6. Defects · 7. Requirements Traceability Matrix

## 1. Strategy (copy the relevant parts into 02-design.md §9)

| Level | What | Tools | Location | Speed |
|---|---|---|---|---|
| Unit | domain rules, services with in-memory fakes, parsers | pytest, hypothesis | `tests/unit/` (mirrors `src/<package>/`) | ms; runs in `make check` |
| Integration | each adapter against the real thing: DB engine, filesystem, HTTP via a local stub, subprocess | pytest + `tmp_path`, SQLite / `testcontainers`, `respx` or a local ASGI app | `tests/integration/` | seconds |
| E2E / acceptance | the user-visible flow: the installed CLI via subprocess, the HTTP API via `TestClient` or a running server, the public library API | pytest + `subprocess` / `fastapi.testclient` (`httpx2`) | `tests/e2e/` | seconds |

- `tests/conftest.py` auto-marks tests under `integration/` and `e2e/`, so `make check` stays fast (`-m "not integration and not e2e"`) while `make test` and CI run everything.
- **Coverage target:** ≥ 90 % branch coverage of `src/` by default (set in the design; enforced by `fail_under`). Coverage is a floor, not the goal: every acceptance criterion needs a test that would fail if the behaviour broke.
- **What is real vs faked** is a design decision: list it in the design. Default: fake at the ports in unit tests, use real adapters in integration tests, and fake nothing you own in e2e tests.

## 2. Writing tests
- **Every test carries the requirement IDs it verifies:**
  ```python
  @pytest.mark.req("AC-003.2")
  def test_rejects_empty_title(client: TestClient) -> None:
      assert client.post("/v1/items", json={"title": ""}).status_code == 422
  ```
  Several IDs are fine: `@pytest.mark.req("FR-003", "NFR-002")`. A module-level `pytestmark = pytest.mark.req("FR-004")` covers a whole file. Malformed IDs fail collection. A regression test for a defect carries the `DEF-###` (and the AC it protects).
- Name tests for the behaviour: `test_<unit>_<behaviour>_<condition>`. Write one behaviour per test and follow Arrange–Act–Assert. Use plain `assert` (pytest rewrites it).
- Test behaviour through public interfaces, not private helpers or call sequences.
- Use `@pytest.mark.parametrize` with `ids=` for tables of cases, and `pytest.raises(ErrorType, match=...)` for error paths. Check the exit code and stderr of CLI errors.
- **Property-based tests** (hypothesis) for parsers, serialisers (round-trip), invariants and anything with a large input space. Keep generated data in strategies near the tests.
- **Fixtures:** small, explicit, function-scoped by default. Use `tmp_path` for files, `monkeypatch.setenv` for config, and factory fixtures for test data. Never use shared mutable module state.
- **Determinism:** no real clock, randomness or network in unit tests. Inject a clock (`now: Callable[[], datetime]`) and seed randomness. Never `sleep`: poll with a timeout, or make time injectable.
- Warnings are errors (`filterwarnings = error`). Fix the cause. To silence a third-party warning, add a targeted `ignore:` with a comment.
- Tests are typed and linted like production code (mypy and ruff cover `tests/`).

## 3. Fakes, mocks & external dependencies
- **Prefer fakes to mocks:** an in-memory implementation of the port (`InMemoryItemRepo`) exercises real behaviour and survives refactors. Mock (`unittest.mock`, `create_autospec`) only at true edges, and always with `autospec` so signatures are checked.
- Don't mock what you don't own. Wrap third-party clients in an adapter, test the adapter in integration, and fake the adapter's port elsewhere.
- HTTP clients: `respx` (for httpx/httpx2), or a tiny local ASGI app. No real third-party calls in the test suite.
- Databases: test against the real engine type used in production (SQLite stays SQLite; Postgres via `testcontainers` when Docker is available, otherwise record a limitation). Wrap each test in a transaction rolled back at teardown, or use a fresh database per test.
- FastAPI dependencies: override with `app.dependency_overrides[get_settings] = lambda: test_settings`. Clear the overrides in teardown.

## 4. Integration & e2e
- **CLI e2e:** run the real entry point: `subprocess.run([sys.executable, "-m", "<package>", ...], capture_output=True, text=True, check=False, timeout=30)`. Assert the exit code, stdout and stderr. `CliRunner` tests are fine at the unit level, but at least one e2e test per command goes through a real process. Coverage of child processes is measured (`patch = ["subprocess"]`).
- **API e2e:** `with TestClient(app) as client:` runs lifespan events. Cover every endpoint row in the design: success, validation (422), auth (401/403), not found (404), and conflict (409) where designed. Compare the generated OpenAPI (`app.openapi()`) against the design's contract for paths and status codes.
- **Library e2e:** import only from the package root (`from pkg import ...`) to prove the public API works as documented. Run docstring examples with `--doctest-modules` if the design promises them.
- **Packaging smoke test** (P4): `make build`, install the wheel into a fresh venv (`uv venv /tmp/smoke && uv pip install --python /tmp/smoke dist/*.whl`), then run the entry point or import the package.

## 5. NFR verification

| NFR type | Method | Evidence in the test report |
|---|---|---|
| Code quality | `make lint typecheck` | "0 errors" output |
| Coverage | `make coverage` | total %, per-module misses |
| Security | `make audit`, ruff `S` clean, review of secrets handling and authz | command output, review notes |
| Performance | `pytest-benchmark` for functions; a load tool (locust, k6, `oha`) against a production-like run for APIs; `time` / `hyperfine` for CLIs | measured numbers vs target, with environment details |
| Compatibility | CI matrix over Python versions / OSes | CI run link or local runs per version (`uv run --python 3.x make test`) |
| Reliability | tests for retries, timeouts, idempotency, graceful shutdown, exit codes | test IDs |
| Packaging | build + install smoke test (§4); image size via `docker image ls` | output |

If a method can't be run here (no Docker, no network, no target hardware), mark the NFR **Not verified** with the reason. Never estimate.

## 6. Defects

| Severity | Meaning | Gate rule |
|---|---|---|
| Critical | Data loss, security hole, crash on the main flow, no workaround | Must be fixed before P4 exits |
| High | A Must requirement fails, or a major flow is broken | Must be fixed before P4 exits |
| Medium | A Should/Could requirement fails, or a workaround exists | Fix, or the user explicitly accepts it at the gate |
| Low | Cosmetic, or a minor inconvenience | Fix, or the user explicitly accepts it at the gate |

Log each one as `DEF-###` in the test report: severity, requirement, steps to reproduce, expected vs actual, status. Fix it with a regression test marked `@pytest.mark.req("DEF-###", "AC-…")`, then re-run the affected suites. If the fix changes design or requirements, raise a CR.

## 7. Requirements Traceability Matrix
1. Run `make rtm`. It prints each requirement ID with its tests and outcomes and writes `rtm.json`.
2. For every FR and NFR in `01-requirements.md`, fill a row in `04-test-report.md` §5: design reference (from the design's coverage table), implementing files (from the implementation log), tests (from `rtm.json`) and status.
3. Status is **Pass** only when every linked test passed and, for NFRs, the measured value meets the target. An FR whose ACs have no tests is **Fail (untested)**.
4. Investigate the `(untraced)` bucket: give each test the ID it supports, or justify it (for example, a test of a shared helper) in the report.
5. All Must rows must be Pass to exit P4.
