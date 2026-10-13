# Software Design Document — <Project name>

| Version | Date | Implements | Status |
|---|---|---|---|
| 1.0 | <YYYY-MM-DD> | 01-requirements.md v<x> | Draft |

**Changelog:** 1.0 — initial baseline.

## 1. Overview & architecture
<!-- Small text diagram of the runtime: entry point, layers, external systems. -->
```
[CLI: typer app] ──▶ [services] ──▶ [repositories] ──▶ [SQLite file]
                                 └─▶ [HTTP client] ──▶ [3rd-party API]
```

## 2. Technology stack
<!-- The profile from references/tech-stack.md §2 for this product type; list deviations with ADR refs. Resolved versions go in the implementation log, not here. -->

| Concern | Choice | ADR |
|---|---|---|
| Python | CPython <3.x> (`requires-python = ">=3.x"`) | — |
| Project & env | uv (`uv_build` backend, `uv.lock`) | — |
| Lint/format · types · tests | ruff · mypy --strict · pytest + hypothesis | — |
| … | | |

## 3. Package structure & module boundaries
```
src/<package>/
  __init__.py   __main__.py   py.typed
  config.py          # settings, loaded once at the edge
  domain/            # pure models + rules, no I/O
  services/          # use cases; depend on ports (Protocols), not adapters
  adapters/          # db, http clients, filesystem — implement the ports
  entrypoints/       # cli.py / api.py — parse input, call services, render output
tests/
  unit/  integration/  e2e/  conftest.py
```
<!-- List each module: what it owns, what it may import. Dependencies point inward: entrypoints → services → domain; adapters → domain. -->

| Module | Owns | May import |
|---|---|---|
| | | |

## 4. External interface
<!-- Keep the table(s) for this product type; delete the others. Every row cites FRs. -->

**CLI commands**

| Command & arguments | Output (stdout) | Exit codes | FRs |
|---|---|---|---|
| `<prog> add <amount> [--note TEXT]` | `Added #<id>` | 0 ok · 2 usage · 1 error | FR-001 |

**HTTP API** (the OpenAPI document generated from code must match this)

| Method & path | Request | Response (2xx) | Errors | Auth | FRs |
|---|---|---|---|---|---|
| `POST /v1/items` | `ItemCreate` | `201 Item` | 401, 409, 422 | Bearer | FR-001 |

**Public Python API** (everything else is private: `_name`, not in `__all__`)

| Symbol | Signature | Raises | FRs |
|---|---|---|---|
| `parse(text: str) -> Doc` | | `ParseError` | FR-001 |

## 5. Data model
<!-- Real code: these are copied into src/ in P3. Domain = dataclasses/attrs; boundary = Pydantic models; persistence = SQLAlchemy models + migration plan. -->
```python
@dataclass(frozen=True, slots=True)
class Item:
    id: ItemId
    title: str
    created_at: datetime  # always timezone-aware (UTC)


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: Annotated[str, Field(min_length=1, max_length=200)]
```

Persistence: <tables, indexes, constraints, migration tool and policy — or N/A>

## 6. Error handling
<!-- Exception hierarchy, where errors are translated (adapters → domain errors → entrypoint renders), what the user sees. -->

| Error | Raised by | Mapped to | FRs/NFRs |
|---|---|---|---|
| `ItemNotFound(DomainError)` | services | CLI: exit 1 + message · API: 404 problem+json | FR-002 |

## 7. Configuration & secrets

| Setting | Env var | Type / default | Secret? | Notes |
|---|---|---|---|---|
| Database URL | `APP_DATABASE_URL` | `str`, required | Yes | from the environment, never committed |

## 8. Cross-cutting concerns
- **Concurrency model:** <sync · asyncio (and why) · threads/processes for CPU work>
- **Logging & observability:** <stdlib logging / structlog; format per environment; what's never logged>
- **Security:** <input validation at boundaries, authn/z, subprocess/SQL safety, dependency policy>
- **Performance:** <budget from NFRs, known hot paths, caching, pagination>
- **Compatibility:** <Python versions and OSes tested in CI>

## 9. Test strategy
<!-- From references/testing.md §1: levels, tools, what's faked vs real, coverage target, how NFRs are verified. -->

| Level | Scope | Tools | Location | Runs in |
|---|---|---|---|---|
| Unit | domain, services with fakes | pytest, hypothesis | `tests/unit` | `make check` |
| Integration | adapters against real deps | pytest, <testcontainers / tmp SQLite / respx> | `tests/integration` | `make test`, CI |
| E2E | installed entry point / running app | pytest + subprocess / httpx | `tests/e2e` | `make test`, CI |

Coverage target: <90 %> branch on `src/`.

## 10. Build order (Phase 3 plan)

| # | Module | Delivers | Depends on |
|---|---|---|---|
| 1 | Foundation: `uv init`, tooling config, package skeleton, `make check` green | NFR-001 | — |
| 2 | Domain models & errors | FR-… | 1 |
| 3 | Ports + adapters (<db/http>) | FR-… | 2 |
| 4 | Services (use cases) | FR-… | 2, 3 |
| 5 | Entry point: <CLI/API> | FR-… | 4 |
| 6 | Config, logging, packaging polish | NFR-… | 5 |

## 11. Requirements coverage
<!-- Every FR/NFR → design section(s). Any requirement without a row blocks the gate. -->

| Req | Design sections |
|---|---|
| FR-001 | §4, §5 |

## 12. Architecture Decision Records

### ADR-001 — <decision title>
- **Status:** Accepted
- **Context:** <forces, requirement IDs>
- **Decision:** <what we chose>
- **Alternatives:** <what we didn't, and why>
- **Consequences:** <trade-offs accepted>
