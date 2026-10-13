---
paths:
  - "pyproject.toml"
  - "uv.lock"
---

# Dependency rules

- **Approval:** add only packages named in `02-design.md` or approved through a CR. A package outside the tech-stack profile needs an ADR.
- **Adding:** use `uv add <pkg>` (or `uv add --dev <pkg>`) so uv resolves the current release and updates `uv.lock`. Don't type versions from memory, and never hand-edit `uv.lock`.
- **Before adding,** check that the package is actively maintained, has a licence compatible with the project, supports the project's Python version and platforms, and ships wheels. Prefer the standard library when it is enough.
- **Constraints:** apps keep uv's default lower bounds, with `uv.lock` as the exact record. Libraries use lower bounds only (no upper caps) and test the range in CI. No git/path/URL dependencies without an ADR.
- **Groups:** dev tools go in the `dev` dependency group. Optional runtime features go in `[project.optional-dependencies]` extras.
- **After a change,** run `make check`. Run `make audit` before any gate.
- **Major upgrades** (frameworks, a new Python minor, uv) are CRs followed by a full P4 regression.
