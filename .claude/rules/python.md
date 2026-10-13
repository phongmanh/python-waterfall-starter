---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
  - "scripts/**/*.py"
---

# Python rules

Full standard: `.claude/skills/python-waterfall/references/best-practices.md`. The non-negotiables:

- **Match the approved design:** module boundaries, signatures, models, CLI commands, endpoints and error mapping. A difference needs a CR, not a quiet fix.
- **Types:** `mypy --strict` stays clean. Use modern syntax (`list[int]`, `X | None`, PEP 695 generics). No `Any` in signatures. External data is `object` until a Pydantic model or `TypeAdapter` parses it. Every `# type: ignore[code]`, `cast()` and `# noqa: CODE` has a reason and goes in the implementation log.
- **Structure:** the domain is pure (no I/O, no framework imports). Adapters do I/O behind `Protocol` ports. Entry points stay thin and are the composition root. No import-time side effects.
- **Data:** domain types are `@dataclass(frozen=True, slots=True)`. Boundary models are Pydantic with `extra="forbid"` on inputs. Datetimes are timezone-aware UTC. Money is `Decimal`. Paths are `pathlib.Path`.
- **Errors:** use the package's exception hierarchy and `raise … from err`. No bare `except:`, and no swallowed exceptions. A broad `except Exception` is allowed only at a process boundary, where it logs and translates the error.
- **Resources:** use context managers for everything closable. Open text files with `encoding="utf-8"`. Every network call has a timeout. Subprocess calls use list args, never `shell=True`.
- **Logging:** `logger = logging.getLogger(__name__)` with lazy `%s` formatting. Libraries never configure logging. No `print` outside CLI output, and no secrets or PII in logs.
- **Config:** one `Settings` class (pydantic-settings), read at the edge. Never read `os.environ` deep in the code.
- **No mutable default arguments.** Use keyword-only parameters for options and flags. Public APIs get docstrings (Google style).
- After editing, the PostToolUse hook runs `ruff check --fix` + `ruff format` on the file. Fix whatever it reports before moving on.
