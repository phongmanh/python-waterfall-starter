# Tech stack & project setup

Contents: 1. Baseline toolchain · 2. Profiles by product type · 3. Project setup · 4. Config notes · 5. Make targets · 6. CI & release · 7. When to deviate

The setup below was verified end to end in October 2026 (scaffold → `make check` → coverage → `make rtm` → `make audit` → `make build` → pre-commit): uv 0.13, CPython 3.14, ruff 0.17, mypy 2.4, pytest 9.1, pytest-cov 7.1, hypothesis 6.169, FastAPI 0.143, SQLAlchemy 2.1, Pydantic 2.14, pydantic-settings 2.15, Typer 0.27, httpx2 2.13. The `Dockerfile` follows uv's Docker guide but was not built during verification (no Docker daemon). Tools move fast: if something no longer matches a tool's current docs, follow the docs and note the change in the implementation log.

## 1. Baseline toolchain (every profile)

| Concern | Choice | Why |
|---|---|---|
| Python | Newest CPython every dependency supports (3.14 as of Oct 2026; 3.15 is brand new, so check wheels first) | Speed, typing features, longest support window |
| Project, env, lock, build, publish | **uv** (`uv_build` backend, `uv.lock`, PEP 735 `dev` group) | One fast tool; reproducible `--locked` installs |
| Layout | **src layout** + `py.typed` | Tests run against the installed package, not the working tree |
| Lint + format | **ruff** (broad rule set incl. bandit `S`) | Replaces black, isort, flake8 + plugins, pyupgrade |
| Types | **mypy --strict** | Mature, plugin ecosystem (pydantic). `ty` is still 0.0.x: revisit when stable |
| Tests | **pytest** + **pytest-cov** (branch) + **hypothesis** | Fixtures, markers, property-based tests |
| Hooks | **pre-commit** (or `prek`, a faster drop-in) | Same checks before every commit |
| Audit | `uv audit` (OSV database; preview feature in uv 0.13) | No extra tool |
| Tasks | `Makefile` calling `uv run …` | Universal, one name per check (`make check`) |
| Config | **pydantic-settings** for apps with settings | Typed, validated env config; `SecretStr` for secrets |
| Logging | stdlib `logging` (libraries); **structlog** for services that need JSON logs | Libraries must not configure logging |

## 2. Profiles by product type

Pick one in P2; anything else is an ADR.

| Profile | Runtime deps (`uv add …`) | Extra dev deps (`uv add --dev …`) | Notes |
|---|---|---|---|
| **CLI tool** | `typer` (pulls in `rich`) | — | `[project.scripts] prog = "pkg.cli:app"`. Test with `typer.testing.CliRunner`, plus an e2e test that runs the installed script via subprocess. Tiny, dependency-free tools may use `argparse` (ADR). |
| **Web API / service** | `fastapi uvicorn pydantic-settings` (+ `sqlalchemy alembic` with a database, + `structlog`) | `httpx2` | Starlette's `TestClient` now wants **`httpx2`**; with `httpx` it emits a deprecation warning that our `filterwarnings = error` turns into a failure. Use `httpx2` for outbound HTTP too. Add `plugins = ["pydantic.mypy"]` to `[tool.mypy]`. Sync endpoints + sync SQLAlchemy unless an NFR needs async (ADR). |
| **Library / SDK** | none by default; keep runtime deps minimal and lower-bounded | — | `uv init --lib` instead of `--package` (no script). Public API in `__all__`; everything else `_private`. Support every Python version still maintained, unless the requirements say otherwise (CI matrix). |
| **Worker / pipeline** | `pydantic-settings structlog` (+ the queue/DB client the design picks) | — | Idempotent steps, explicit retries with backoff, graceful shutdown on SIGTERM. |

Databases: SQLAlchemy 2.x typed ORM (`Mapped[...]`, `mapped_column`) + Alembic migrations. Integration tests run against the real engine (SQLite for SQLite apps; `testcontainers` for Postgres/MySQL, ADR if Docker is required in CI).

## 3. Project setup (P3, step 1)

By P3 the project root already contains `docs/waterfall/` and this repo's `README.md`. `uv init` doesn't overwrite existing files and, with `--no-readme`, leaves the README alone.

```bash
# in the project root (contains docs/waterfall/)
uv --version            # 0.13+. Missing? Ask the user to install uv: https://docs.astral.sh/uv/
uv python list          # confirm the Python version chosen in 02-design.md is available

# CLI / service / worker:
uv init --package --vcs none --no-readme --python 3.14 --name <dist-name> .
# library:  uv init --lib --vcs none --no-readme --python 3.14 --name <dist-name> .

uv add --dev ruff mypy pytest pytest-cov hypothesis
uv add <runtime deps from the profile>          # e.g. uv add typer
uv add --dev <extra dev deps from the profile>  # e.g. uv add --dev httpx2

S=.claude/skills/python-waterfall/assets/scaffold
cat $S/pyproject.tools.toml >> pyproject.toml   # then replace PACKAGE with the import name
cp $S/Makefile .
mkdir -p tests/unit tests/integration tests/e2e
cp $S/tests/conftest.py tests/
touch src/<package>/py.typed                    # --lib creates it; --package doesn't
cp $S/.pre-commit-config.yaml .
uvx pre-commit autoupdate && uvx pre-commit install   # needs a git repo
make check
```

Notes:
- `--vcs none` because version control is the user's decision (the skill offers `git init` separately).
- `uv init --package` writes a demo `main()` that prints. Replace it with the design's entry point; `T20` (no `print`) will flag it otherwise.
- After `cat`-ing the tool config, edit `pyproject.toml`: fill in `description`, set the coverage `fail_under` to the target from the design, add mypy plugins the profile needs, and point `[project.scripts]` at the real entry point.
- Then create the package structure from best-practices.md §3. A green `make check` before the first feature module proves the tooling works.

## 4. Config notes (`pyproject.tools.toml`)

- **ruff** selects a broad set: pycodestyle, pyflakes, isort, naming, pyupgrade, bugbear, builtins, comprehensions, timezone-aware datetimes, no `print`, pytest style, returns, simplify, unused args, pathlib, no commented-out code, pylint, exception handling, perf, bandit security, logging. `TRY003` and `PLR2004` are ignored globally; tests may `assert` and use magic numbers.
  - **`TC` (type-checking imports) is deliberately off.** Its fixes move imports under `if TYPE_CHECKING:`, which breaks FastAPI, Pydantic, SQLAlchemy and Typer, because they evaluate annotations at runtime. Ruff marks those fixes unsafe for this reason.
  - `.claude/` is excluded: the hook scripts are stdlib-only and Python 3.9-compatible on purpose.
- **mypy**: `strict = true`, `warn_unreachable`, extra error codes (`ignore-without-code`, `redundant-expr`, `truthy-bool`, `possibly-undefined`). Checks `src` and `tests`.
- **pytest 9** native `[tool.pytest]` table: `--strict-markers`, `--strict-config`, `--import-mode=importlib`, `xfail_strict`, and **`filterwarnings = ["error"]`** (deprecations fail tests, so upgrades surface them immediately; silence a specific third-party warning with a targeted `ignore:` entry plus a comment). The `req` marker is registered.
- **coverage**: branch coverage, `patch = ["subprocess"]` so e2e tests that run the installed program in a child process are measured too, and `fail_under` set to the design's target.

## 5. Make targets

| Target | Runs | When |
|---|---|---|
| `make check` | ruff format --check, ruff check, mypy, fast tests | after every module (the P3 gate) |
| `make fmt` | ruff format + safe fixes | any time |
| `make test` | all tests | end of P3, P4 |
| `make coverage` | all tests + branch coverage, fails under target | P4, CI |
| `make rtm` | requirement → tests → outcome, writes `rtm.json` | P4 RTM, CI |
| `make audit` | `uv audit --locked` | P4 (security NFR), CI |
| `make build` | `uv build` → `dist/` | P3 finish, P5 |

## 6. CI & release (P5)

- **CI:** copy `assets/scaffold/.github/workflows/ci.yml`. It uses `astral-sh/setup-uv` with caching; uv installs the Python from `.python-version`. For a compatibility matrix, add `strategy.matrix.python-version` and pass it as `setup-uv`'s `python-version` input. Keep `permissions: contents: read`.
- **PyPI:** use trusted publishing (OIDC) from a tag-triggered workflow (`uv build` then `uv publish`), never a long-lived API token. Publishing is outward-facing: confirm with the user first.
- **Container:** copy `assets/scaffold/Dockerfile` + `.dockerignore`. Multi-stage: deps layer cached on `uv.lock`, `--no-dev --no-editable`, runtime on `python:<ver>-slim-trixie`, non-root user, no uv in the final image. Pin the uv image to a minor (`0.13`) and bump deliberately.
- **Version:** `uv version 1.0.0` sets it in `pyproject.toml`. Tag releases `v1.0.0`.

## 7. When to deviate (record an ADR)

- An org standard mandates Poetry/PDM/Hatch, pyright, or tox/nox.
- A library must support Python versions older than the profile default (CI matrix, `requires-python` lower bound, no newer syntax).
- Async I/O is required by an NFR (high-concurrency I/O, websockets): async FastAPI + async SQLAlchemy + `pytest-anyio`.
- Heavy data work: Polars/pandas/NumPy, and maybe notebooks; keep notebooks out of `src/`, and test the library code they call.
- No Docker in CI: integration tests use SQLite or fakes behind the same port, and the gap is recorded as a limitation.
