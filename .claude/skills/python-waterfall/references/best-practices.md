# Python best practices

The coding standard for P3. ruff and mypy enforce much of it mechanically. The rest is judgment, checked per module with §14.

Contents: 1. Principles · 2. Typing · 3. Project structure · 4. Functions & classes · 5. Data modelling · 6. Errors · 7. Boundaries & validation · 8. Configuration · 9. I/O, resources & concurrency · 10. Logging · 11. Security · 12. Performance · 13. Style & docs · 14. Per-module review checklist

## 1. Principles
- **The design is the spec.** Names, signatures, models, commands and endpoints match `02-design.md`. A difference needs a CR.
- **Functional core, imperative shell.** Domain logic is pure and has no I/O. Adapters do I/O. Entry points wire things together. This makes logic unit-testable without mocks.
- **Dependencies point inward:** entrypoints → services → domain; adapters implement ports defined next to the services. The domain never imports a framework.
- **Explicit over implicit.** No hidden global state, no import-time side effects (no I/O, network, env reads or logging config at import), no monkey-patching in production code.
- **KISS, YAGNI.** The simplest design that meets the approved requirements. No speculative abstraction; a second implementation justifies an interface.
- **Boy Scout rule** applies within the CR process: tidy what you touch; don't refactor untouched modules without a CR.

## 2. Typing
- Every function, method and module-level variable whose type isn't obvious is annotated. `mypy --strict` passes with zero errors.
- Use modern syntax: `list[int]`, `X | None`, `type Alias = ...` (3.12+), PEP 695 generics `def first[T](xs: Sequence[T]) -> T`, `typing.Self`, `@override` on overridden methods.
- Accept the most general type and return the most specific: parameters take `Iterable`/`Sequence`/`Mapping`; return `list`/`dict`.
- **No `Any`** in signatures. External data is `object` until validated (§7). `cast()` only with a comment explaining why it's true.
- `# type: ignore[code]` always has an error code and a reason (mypy enforces the code). Log it in the implementation log.
- Model alternatives as closed unions and handle them exhaustively: `match` + `assert_never(x)` in the default branch.
- Use `Protocol` for ports (structural typing), `NewType` for IDs that must not be mixed (`UserId = NewType("UserId", int)`), `Literal` for small closed sets, `enum.StrEnum` when values need behaviour or iteration.
- `Final` for constants, and `TYPE_CHECKING` imports only to break real import cycles. (Ruff's `TC` rules are off; see tech-stack.md §4.)

## 3. Project structure

```
src/<package>/
  __init__.py      # public API re-exports + __all__ (libraries); minimal for apps
  __main__.py      # `python -m <package>` → entrypoints
  py.typed
  config.py        # Settings (pydantic-settings), constructed once at the edge
  errors.py        # exception hierarchy root: class <Package>Error(Exception)
  domain/          # entities, value objects, rules: pure, no I/O, no framework imports
  services/        # use cases; depend on ports (Protocols) defined here
  adapters/        # db, http clients, filesystem, queues: implement the ports
  entrypoints/     # cli.py / api.py: parse → call service → render; thin
tests/
  conftest.py      # traceability plugin + shared fixtures
  unit/            # mirrors src/<package>/ ; no I/O
  integration/     # adapters against real dependencies
  e2e/             # installed entry point / running app
```
- Small projects may flatten (`models.py`, `service.py`, `cli.py`), but the import direction rule still holds. Record the structure in the design.
- One module, one responsibility. Split modules beyond ~400 lines by responsibility. Avoid `utils.py` grab-bags: name modules for what they do.
- No circular imports. If two modules need each other, a third concept is missing.
- Libraries: the public API is exactly what `__init__.py` exports in `__all__`. Everything else is `_private`.

## 4. Functions & classes
- Functions do one thing, ideally under ~40 lines, with at most ~5 parameters. Use keyword-only parameters (`*,`) for flags and options: `def export(items, *, fmt: Format = "csv")`.
- **Never use mutable default arguments.** Use `None` plus creation inside the function, or `field(default_factory=...)`.
- Prefer functions and plain data over classes. Use a class when there is state with invariants, or a port implementation.
- Prefer composition and dependency injection: pass collaborators into constructors and functions. Construct the object graph in the entry point (the composition root). No service locators.
- Return early instead of nesting. No boolean "mode" parameters that switch behaviour; write two functions.
- Generators for streams, comprehensions for simple transforms; explicit loops when the logic has branches.
- Use `@functools.cache` / `lru_cache` only on pure functions, and never on methods (it leaks `self`).

## 5. Data modelling
- **Domain objects:** `@dataclass(frozen=True, slots=True, kw_only=True)` by default. Immutability makes reasoning and testing easy. Validate invariants in `__post_init__` and raise a domain error.
- **Boundary models** (HTTP bodies, config, files, external APIs): Pydantic v2 `BaseModel` with `model_config = ConfigDict(extra="forbid")` for inputs. Use `Annotated[..., Field(...)]` constraints.
- Keep the two apart: don't pass Pydantic request models into the domain. Map at the entry point or service boundary.
- **Datetimes are timezone-aware, in UTC** (`datetime.now(UTC)`). Ruff `DTZ` enforces this. Convert to local time only for display.
- Money is `Decimal` (or integer minor units), never `float`. Use `pathlib.Path`, never path strings (`PTH`).
- Persistence: SQLAlchemy 2.x typed models (`Mapped[...]`) live in adapters, never in the domain. Every schema change gets an Alembic migration, reviewed, with a downgrade.

## 6. Errors
- Define one root exception per package (`class BudgetError(Exception)`) and specific subclasses for conditions callers handle (`ItemNotFound`, `InvalidAmount`).
- Raise specific exceptions with context; chain with `raise X(...) from err`. Never `raise Exception`.
- Catch the narrowest exception, as close to where you can handle it as possible. **No bare `except:`, and no `except Exception: pass`.** A broad catch is allowed only at a process boundary (entry point, worker loop, hook), where it logs with `logger.exception` and translates into an exit code or HTTP response.
- Translate at layers: adapter errors (e.g. `sqlalchemy.exc.IntegrityError`) become domain errors in adapters; domain errors become user output (exit code + message, or HTTP status + problem body) in entry points. The design's error table is the contract.
- `assert` is for internal invariants in tests, never for validation (asserts are stripped with `-O`; ruff `S101`).
- CLI: errors go to stderr with a human message and a non-zero exit code (1 for errors, 2 for usage). Show tracebacks only with `--debug`.

## 7. Boundaries & validation
- **Parse, don't validate:** convert untrusted input into typed, validated objects at the edge, once. Inner code trusts types. Untrusted input means CLI args, HTTP, env, files, queue messages and third-party API responses.
- Validate with Pydantic (`Model.model_validate(data)` / `TypeAdapter`) or the framework (FastAPI, Typer) that does it for you. Reject unknown fields on inputs.
- Normalise early (strip, casefold, timezone-convert). Enforce sizes and limits explicitly: max lengths, max upload size, pagination caps.

## 8. Configuration
- All settings in one `Settings(BaseSettings)` class with an env prefix. Read it once in the entry point and pass it down, or provide it through a cached `get_settings()` dependency. Never read `os.environ` deep in the code.
- Secrets are `SecretStr`, come only from the environment or a secret manager, and never get defaults that look real. `.env.example` lists names with dummy values; `.env` is git-ignored.
- Fail fast at startup on missing or invalid config, with a clear message.

## 9. I/O, resources & concurrency
- Always use context managers for files, connections, sessions and locks (`with`, `contextlib.ExitStack`). Never leave a resource for GC to close.
- Text files: always `encoding="utf-8"`. Subprocess: list arguments, `check=True` (or inspect the return code), a `timeout`, never `shell=True` with interpolated input.
- **Every network call has a timeout.** Retries are explicit, bounded, use backoff, and only cover idempotent operations.
- Choose sync or async per the design. Don't mix: no blocking calls (`requests`, `time.sleep`, sync DB drivers) inside `async def`; offload with `anyio.to_thread.run_sync` if unavoidable. Keep references to created tasks, use `TaskGroup` for structured concurrency, and propagate cancellation.
- CPU-bound work goes to processes (`concurrent.futures.ProcessPoolExecutor`), or to free-threaded Python only via an ADR.

## 10. Logging
- Get one logger per module: `logger = logging.getLogger(__name__)`. **Libraries never configure logging**; applications configure it once in the entry point.
- Use lazy formatting: `logger.info("Imported %d rows from %s", n, path)`, not f-strings (`G004`). Use `logger.exception` inside `except` blocks.
- Levels: DEBUG for diagnostics, INFO for business events, WARNING for recoverable anomalies, ERROR for failed operations. Never log-and-raise the same error twice up the stack.
- **Never log secrets, tokens, passwords, full request bodies or PII.** Services emit structured (JSON) logs in production, with a request or correlation ID.
- No `print` outside CLI output paths (`T20`). CLI output goes through `typer.echo` / `rich`, which is separate from logging.

## 11. Security
- Ruff's bandit rules (`S`) stay on. Fix findings; don't suppress them without a reason.
- **SQL:** ORM or bound parameters only, never string-built SQL. **Shell:** `subprocess.run([...])` without `shell=True`. **Deserialisation:** no `pickle`/`marshal`/`yaml.load` on untrusted data (`yaml.safe_load`). **Templates:** autoescape on.
- No `eval`/`exec` on input. Paths from input: resolve them and check they stay inside the allowed directory (`path.resolve().is_relative_to(base)`).
- Crypto and secrets: the `secrets` module for tokens; `hashlib` only with modern algorithms; passwords with argon2/bcrypt via a vetted library (ADR). Compare secrets with `hmac.compare_digest`.
- HTTP services: authn and authz on every endpoint (deny by default), CORS restricted to known origins, request size limits, rate limiting where NFRs say so, and generic error messages (no stack traces to clients).
- Dependencies: only what the design names (or an approved CR adds), with `uv.lock` committed, `uv sync --locked` in CI, and `make audit` clean.

## 12. Performance
- Measure before optimising (`cProfile`, `py-spy`, `pytest-benchmark` for NFR-backed hot paths). Record numbers in the test report.
- Choose the right data structure first (`set`/`dict` lookups, `collections.deque`, `heapq`), then batch I/O (bulk inserts, connection pooling, pagination, streaming large files) instead of loading everything into memory.
- Avoid N+1 queries: eager-load relationships the view needs (`selectinload`).

## 13. Style & docs
- ruff format output is the style; don't argue with it. Naming: `snake_case` functions and variables, `PascalCase` classes, `UPPER_SNAKE` constants, `_leading_underscore` for private.
- Docstrings (Google style) on every public module, class and function. Say *what* and *why*, plus `Args`/`Returns`/`Raises` when not obvious from types. Comments explain why, not what. No commented-out code (`ERA`).
- No magic values with meaning: name them as constants or enums.
- Each requirement-relevant behaviour has its test carrying the ID; don't put requirement IDs in production code comments unless the code exists solely for that requirement.

## 14. Per-module review checklist (P3)
Walk this before logging a module as done:
- [ ] Matches the design: names, signatures, models, interface rows, module boundaries. Anything else is a logged in-latitude decision or a CR.
- [ ] `make check` is green. No new `# noqa`, `# type: ignore` or `cast` without a code and a reason (logged).
- [ ] Domain code is pure. I/O lives in adapters. The import direction is respected and there are no import-time side effects.
- [ ] Untrusted input is validated at the boundary. Every error path maps to the design's error table.
- [ ] Resources use context managers. Network calls have timeouts. Subprocess calls don't use the shell.
- [ ] No secrets, PII or tokens in code, logs or test fixtures. Config goes through Settings.
- [ ] Tests cover each acceptance criterion this module delivers (`@pytest.mark.req`), the edge cases and the error paths. Property-based tests cover parsers and invariants.
- [ ] Public functions and classes have docstrings. No dead code and no TODOs without an owner.
- [ ] The implementation log has a row for this module, with FRs, files, tests and deviations.
