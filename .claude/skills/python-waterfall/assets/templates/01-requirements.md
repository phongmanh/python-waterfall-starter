# Software Requirements Specification — <Project name>

| Version | Date | Author | Status |
|---|---|---|---|
| 1.0 | <YYYY-MM-DD> | Claude with <user> | Draft |

**Changelog:** 1.0 — initial baseline.

## 1. Purpose & success criteria
<!-- One paragraph: what problem this software solves and for whom. Then 2–4 measurable success criteria. -->
- SC-1:

## 2. Product type & users
<!-- Product type drives the design profile: CLI tool · Web API/service · Library/SDK · Worker/pipeline · other (say what). -->
- **Product type:**
- **Runs where:** <developer laptops / server / container / serverless / user installs from PyPI>

| User / client | Description | Key goals | Permissions |
|---|---|---|---|
| | | | |

## 3. Functional requirements
<!-- One observable behaviour per FR. Priority = MoSCoW (Must / Should / Could / Won't).
     Each FR has ≥1 acceptance criterion in Given/When/Then. IDs are permanent.
     Observable means: CLI output + exit code, HTTP status + body, return value / raised exception, file or DB state. -->

### FR-001 — <short name> (Must)
**User story:** As a <user>, I want <capability> so that <benefit>.

| AC | Given | When | Then |
|---|---|---|---|
| AC-001.1 | | | |
| AC-001.2 | | | |

### FR-002 — <short name> (Should)
**User story:** …

| AC | Given | When | Then |
|---|---|---|---|
| AC-002.1 | | | |

## 4. Non-functional requirements
<!-- Every NFR measurable and with a verification method. Defaults shown — keep the rows that fit the product type, delete or N/A the rest, and adjust numbers with the user. -->

| ID | Category | Requirement | Verification | Priority |
|---|---|---|---|---|
| NFR-001 | Code quality | `ruff` and `mypy --strict` report 0 errors; no unexplained suppressions | `make check` | Must |
| NFR-002 | Test coverage | Branch coverage ≥ 90 % of `src/` | `make coverage` | Must |
| NFR-003 | Security | No known-vulnerable dependencies; no secrets in the repo; all external input validated | `make audit` + ruff `S` rules + review | Must |
| NFR-004 | Compatibility | CPython <3.x>+ on <Linux / macOS / Windows> | CI matrix | Must |
| NFR-005 | Performance | <API: p95 latency < N ms at M req/s · CLI: `--help` < 300 ms, job X < N s · Library: op Y < N µs> | <load test / timing / pytest-benchmark> | Should |
| NFR-006 | Reliability | <API: health endpoint, graceful shutdown · Worker: idempotent retries · CLI: non-zero exit + message on every error path> | tests | Should |
| NFR-007 | Observability | <structured logs (JSON in prod), no PII/secrets in logs, request IDs> | review + tests | Should |
| NFR-008 | Packaging | <installable with `uv tool install` / `pip install`; container image < N MB> | `make build` + install smoke test | Could |

## 5. Data
<!-- Entities read/written, key fields, ownership, retention, PII. -->

| Entity | Key fields | Source of truth | Notes (PII, limits, retention) |
|---|---|---|---|
| | | | |

## 6. External interfaces
<!-- Inbound: CLI commands / HTTP API / public Python API. Outbound: databases, third-party APIs, queues, files. Existing contracts (OpenAPI, schemas)? Auth? Say if something doesn't exist yet. -->

## 7. Constraints
<!-- Deadline, hosting, budget, mandated tech, minimum Python version, existing code, licensing. -->

## 8. Assumptions

## 9. Out of scope
<!-- Explicit list. Anything here needs a CR to come back in. -->
-

## 10. Open questions

| # | Question | Owner | Due | Resolution |
|---|---|---|---|---|
| | | | | |
