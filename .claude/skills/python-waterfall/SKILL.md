---
name: python-waterfall
description: Builds Python software end to end with the Waterfall SDLC — Requirements → Design → Implementation → Testing → Deployment → Maintenance — writing one deliverable per phase into docs/waterfall/ and stopping for the user's explicit sign-off before each next phase, with requirement-to-test traceability (pytest req markers + RTM) and verified best-practice defaults (uv, src layout, ruff, mypy --strict, pytest + hypothesis, pre-commit, Pydantic at the boundaries; Typer for CLIs, FastAPI + SQLAlchemy for APIs). Use this whenever the user wants to build, create, plan or spec a Python CLI, web API, service, library, worker or data pipeline using a waterfall, phased, stage-gated, SDLC, spec-first or "requirements and design before code" process; asks for an SRS, design document or traceability matrix for Python software; or wants to resume, change or extend a project that already has docs/waterfall/STATUS.md — even if they don't say "waterfall". Not for a one-off script or throwaway snippet with no process wording.
---

# Python Waterfall

Build Python software the Waterfall way: six phases, strictly in order, each ending in a written deliverable the user signs off before the next phase starts. The documents are the contract. Later phases implement exactly what earlier phases approved, and every requirement is traced through design and code to a passing test.

The point of the method is to make decisions once, in writing, at the cheapest moment. A missing requirement costs a sentence in Phase 1, a table row in Phase 2, and a rewrite in Phase 3. So this skill front-loads the thinking and never speeds past a gate.

```
P1 Requirements ─▶ P2 Design ─▶ P3 Implementation ─▶ P4 Testing ─▶ P5 Deployment ─▶ P6 Maintenance
 01-requirements    02-design     code +               04-test-       05-deployment    06-maintenance
                                  03-implementation-log  report                         + README → closed
        ▲ gate          ▲ gate          ▲ gate             ▲ gate         ▲ gate           ▲ gate
```

Every deliverable lives in `<project>/docs/waterfall/`, next to `STATUS.md`, which records the current phase, sign-offs and change requests. STATUS.md is what lets a later session pick up exactly where this one stopped.

## Start or resume

1. **Find the project directory.** In this starter repo it is the repository root. Elsewhere, if the user hasn't named one and the working directory isn't obviously it, ask; for a new project propose `./<project-name>/`. Never scaffold into a home directory or an unrelated repo.
2. **Resume** if `<project>/docs/waterfall/STATUS.md` exists: read it and every approved phase document, tell the user in one or two lines where things stand, and continue the current phase. Don't redo approved work.
3. **Start fresh** otherwise: create `docs/waterfall/`, copy `assets/templates/STATUS.md` from this skill into it, fill in the project name, root and today's date, and begin Phase 1.

Each phase starts by copying its template from `assets/templates/` and filling it in. Remove the `<!-- guidance -->` comments as you go. Write `N/A — <reason>` for sections that genuinely don't apply, so a reader can tell "considered and excluded" from "forgotten". Scale depth to the project: a small CLI's design doc can be two pages.

## Rules that hold in every phase

### 1. One phase at a time
Do only the current phase's work. In P1 and P2, write no application code, don't run `uv init` and don't install anything. A premature scaffold anchors decisions the design hasn't made yet. If the user volunteers an implementation idea early, record it (as a constraint in P1, or a design note to revisit in P2) and keep going. The project's hooks enforce this; a blocked tool call means the process is working.

### 2. Hard sign-off gates
When a phase deliverable is complete:
1. Run the `phase-reviewer` agent on the deliverable, fix every blocking finding, and mention any non-blocking ones in your summary.
2. Set the phase to `Awaiting approval` in STATUS.md (and the document header's Status).
3. Present: the document path, a 5–10 line summary of what it decides, open risks or questions, and what the next phase will do.
4. Ask explicitly, e.g. *"Reply **approve** to sign off Phase 1, or tell me what to change."* Then **end your turn**.

Only an unambiguous yes about this phase counts: "approve", "approved", "LGTM", "looks good, go ahead", or `/approve`. Feedback, a question, a conditional ("approve, but…") or an unrelated reply is not approval: revise, re-present and ask again. On approval, set the phase to `Approved` with today's date, set `Current phase` to the next one, log the date and the user's words in the sign-off table, then start the next phase. The approval guard hook only lets STATUS.md mark an item approved in the turn where the user approved it.

The gates are the user's to waive, not yours. If the user is in a hurry, offer leaner documents but keep the gate. Only if the user explicitly says not to stop between phases: record the waiver and their words in STATUS.md's Gate policy row, mark each finished phase `Approved (gate waived)`, and still write every deliverable.

Keep STATUS.md's table layout exactly as in the template (same columns, one row per phase, status in the third column). The hooks parse it.

### 3. Change requests
An approved document is baselined. Any change to behaviour, scope, architecture, data model, interface contract or the stack goes through a change request:
1. Log `CR-###` in STATUS.md: what, why, and which documents, files and tests it affects. Status `Proposed`.
2. Present it and get approval (same gate rules).
3. Update the upstream document (bump its version, add a changelog line), then ripple downstream: requirements → design → code → tests → RTM. Set the CR to `Implemented` when all of it is done and verified.

Typos, broken links and other corrections that don't change meaning need no CR. Unlogged drift is how docs stop being true, and stale docs make traceability worthless. If you find in P3 or P4 that the design is wrong, raise a CR; don't silently code around it.

### 4. Traceability
- Functional requirements are `FR-001`, non-functional `NFR-001`, acceptance criteria `AC-001.1` (under FR-001). Decisions are `ADR-001`, defects `DEF-001`, change requests `CR-001`.
- IDs are never reused or renumbered. A dropped requirement becomes `Withdrawn (CR-###)`.
- Design elements cite the FR/NFR IDs they satisfy. The implementation log maps FRs to files.
- Every test carries the IDs it verifies: `@pytest.mark.req("AC-003.2")`. The scaffold's `tests/conftest.py` rejects malformed IDs, and `make rtm` prints requirement → tests → outcome (and writes `rtm.json`). `grep -rn 'AC-003' tests` also finds the coverage.
- The Requirements Traceability Matrix (RTM) in `04-test-report.md` has a row for every FR and NFR.

### 5. Standards
`references/best-practices.md` is the coding standard, `references/tech-stack.md` the default stack and setup, `references/testing.md` the test guide. If the target project has its own CLAUDE.md, lint config or conventions, those win where they conflict. Record each conflict in the design doc.

---

## Phase 1 — Requirements (what, not how)

**Entry:** STATUS.md exists. **Template:** `assets/templates/01-requirements.md`.

1. **Interview.** Use AskUserQuestion for choices (up to 4 questions per round) and plain questions for open-ended answers. Cover:
   - purpose and measurable success criteria
   - **product type** (CLI tool, web API/service, library/SDK, worker/pipeline, other) and where it runs
   - users or client systems, and their permissions
   - features, as user stories
   - the data handled, and any PII
   - external interfaces: existing APIs, databases, files, queues; existing contracts; auth
   - NFRs: performance, reliability, security, observability, compatibility (Python versions, OSes), packaging
   - constraints: deadline, hosting, budget, mandated tech, existing code, licence
   - what is explicitly out of scope
2. **Propose defaults; don't interrogate.** Offer sensible defaults the user can accept or correct, e.g. "CPython 3.14+, Linux and macOS, ruff + mypy --strict clean, ≥ 90 % branch coverage, no known-vulnerable dependencies". Two or three rounds of questions is usually enough.
3. **Write testable requirements.** Each FR describes one behaviour with an observable outcome (output + exit code, HTTP status + body, return value or exception, stored state) and has at least one Given/When/Then acceptance criterion. NFRs must be measurable ("p95 < 150 ms at 50 req/s", not "fast"). Prioritise with MoSCoW.
4. **Record** assumptions, constraints, out-of-scope items, and open questions with an owner.

**Exit:** every FR has acceptance criteria, every NFR is measurable, out-of-scope is listed, open questions are resolved or explicitly deferred, and the user approves.

## Phase 2 — Design (how)

**Entry:** P1 approved. **Template:** `assets/templates/02-design.md`. **Read first:** `references/tech-stack.md`, `references/best-practices.md`, and `references/testing.md` §1.

Decide and document:
- **Stack.** The profile for the product type in tech-stack.md §2, unless a requirement rules it out. Every deviation or notable choice gets an ADR (Context / Decision / Alternatives / Consequences). Pick the Python version: the newest CPython every chosen dependency supports (check with the user if a platform constrains it).
- **Architecture overview.** A small text diagram: entry point, layers, external systems.
- **Package structure and module boundaries** (src layout, per best-practices.md §3), with the allowed import directions.
- **External interface:** CLI commands with arguments, output and exit codes; or HTTP endpoints with request/response models, errors and auth; or the public Python API with signatures and exceptions. Each row cites FRs.
- **Data model.** Real code for domain types and boundary models (dataclasses / Pydantic), and the persistence schema plus migration policy if there is a database. These are copied into `src/` in P3, so they must be real.
- **Error handling:** the exception hierarchy and where errors are translated for the user.
- **Configuration & secrets:** every setting, its env var, type/default, and whether it's secret.
- **Cross-cutting:** concurrency model (sync vs asyncio, and why), logging/observability, security measures, performance budget, compatibility matrix (all derived from the NFRs).
- **Test strategy:** levels, tools, what is faked vs real, coverage target (testing.md §1).
- **Build order for P3.** A numbered list of modules, each naming the FRs it delivers, ordered by dependency: foundation/tooling → domain → ports & adapters → services → entry point → config/logging/packaging polish.

**Exit:** every FR/NFR maps to at least one design element, every significant choice has an ADR, the build order is complete, and the user approves.

## Phase 3 — Implementation

**Entry:** P2 approved. **Template:** `assets/templates/03-implementation-log.md`. Re-read `02-design.md`; it is the spec.

1. **Scaffold and configure** per `references/tech-stack.md` §3 ("Project setup"): `uv init` next to the existing `docs/`, the dev tools, the tool config from `assets/scaffold/pyproject.tools.toml`, the `Makefile`, `tests/conftest.py` and pre-commit. Record the resolved versions in the log.
2. **Version control.** If the project isn't a git repo, offer to `git init`. Suggest a commit at each module boundary (Conventional Commits citing IDs). Commit only once the user agrees; that agreement can cover the whole project, so note it in STATUS.md's Commit policy row.
3. **Build modules in the design's order.** For each module:
   - Implement it exactly as designed, following best-practices.md.
   - Write its unit tests alongside it, marked with their requirement IDs.
   - Run `make check` (format check + lint + mypy --strict + fast tests). Fix failures before starting the next module; never stack new code on a red build. (The Stop hook also refuses to end a turn while ruff or mypy fail.)
   - Walk the review checklist at the end of best-practices.md.
   - Append a row to the implementation log: module, FRs, files, tests, notes and deviations.
4. **Deviations.** You may decide internal details the design left open (private helpers, internal module splits, local names) and log them. Anything visible in the design doc (commands, endpoints, public API, models, module boundaries, libraries) needs a CR.
5. **Finish** with `make check`, `make test` and `make build` passing and the entry point working (`uv run <prog> --help`, or the API answering locally). Offer to run it so the user can try it before signing off.

**Exit:** every build-order module is done, `make check`, `make test` and `make build` pass, every FR lists its implementing files, and the user approves.

## Phase 4 — Testing & verification

**Entry:** P3 approved. **Template:** `assets/templates/04-test-report.md`. **Read:** `references/testing.md`.

1. Run the full suite with coverage (`make coverage`) and the traceability report (`make rtm`).
2. Fill the gaps: at least one integration or e2e test per acceptance criterion that describes a user-visible flow (CLI invocation, HTTP request, public API call), real adapters against real or containerised dependencies where the design says so, and property-based tests for parsers and invariants.
3. Verify each NFR with the method the requirements named: `make audit` for dependencies, timings or a load test for performance, the CI matrix for compatibility, an install-from-wheel smoke test for packaging.
4. Log every failure as `DEF-###` (severity, requirement, steps, status). Fix it with a regression test carrying the DEF ID, then re-run the affected suites. A fix that changes design or requirements is a CR.
5. Fill the RTM from `rtm.json`: for each FR/NFR, the design reference, files, tests and Pass/Fail. Investigate every `(untraced)` test: give it an ID or justify it.

Report only real results: paste or summarise actual command output. If something couldn't be run (no Docker, no network), say so and mark it not verified. Never estimate a result.

**Exit:** all Must-have requirements pass, no Critical or High defects are open (the user explicitly accepts any lower-severity ones that remain), coverage meets its target or the gap is justified, and the user approves.

## Phase 5 — Deployment

**Entry:** P4 approved. **Template:** `assets/templates/05-deployment.md`.

1. Confirm the release target if the requirements didn't fix it: PyPI package, `uv tool install` from Git, container image + host, serverless, or internal artifact.
2. Add CI from `assets/scaffold/.github/workflows/ci.yml` (lint → types → tests + coverage → RTM → audit → build), plus a compatibility matrix if NFRs require one.
3. Add the release config: the `Dockerfile` + `.dockerignore` from `assets/scaffold/` for container targets (non-root, multi-stage, locked deps); trusted publishing (OIDC) for PyPI rather than API tokens.
4. Document every setting and secret, and add a `.env.example` with names and dummy values. Secrets come from the environment or a secret store only.
5. Set the version to `1.0.0` (`uv version 1.0.0`), start `CHANGELOG.md` (Keep a Changelog format), and write the release checklist and rollback procedure.
6. **Pushing, publishing, deploying, creating remote repos and setting cloud secrets are outward-facing.** Before each one, state exactly what will run and wait for explicit confirmation. If the user prefers to do it themselves, give them the exact commands.

**Exit:** CI passes (or the same steps pass locally if there's no remote yet), the artifact is released or the manual release steps are documented, rollback is documented, and the user approves.

## Phase 6 — Maintenance & handover

**Entry:** P5 approved. **Template:** `assets/templates/06-maintenance.md`.

1. Rewrite the project `README.md` for the software itself: what it is, prerequisites (uv, Python version), setup, usage, `make` targets, package structure, and a link to `docs/waterfall/`. Keep a short "How this was built" section pointing at the waterfall docs.
2. Fill in the maintenance doc: runbook, known issues, accepted defects, dependency update policy (`uv lock --upgrade` cadence, Dependabot/Renovate), monitoring, and the change process (small changes are CRs against the baselined docs; a major version starts a new waterfall cycle).
3. Mark every phase final and the project `Closed — v1.0.0` in STATUS.md, then ask for the closing sign-off.

**After closure,** any new request on this project ("add CSV export") is a CR or a new cycle. Re-enter at Phase 1 with that change; don't edit the code directly.

---

## Guardrails
- No `Any`, `# type: ignore`, `cast()`, `# noqa` or per-file ignore without an error code and a comment explaining why. List each one in the implementation log.
- Don't pin versions from memory. `uv add` resolves current releases and `uv.lock` is the record. If a command or config in the references no longer matches a tool's current docs, follow the docs and note the change in the log.
- Keep documents tight: tables and bullets, concrete names, no filler. A reviewer should be able to read any phase doc in about ten minutes.
- Re-read the approved documents at the start of each phase instead of relying on memory. In long sessions, earlier context may have been summarised.
- Never fabricate test output, coverage, benchmark numbers, audit results or deploy results.

## Reference map

| File | When to read |
|---|---|
| `references/best-practices.md` | Before P2; consult throughout P3; use its checklist per module |
| `references/tech-stack.md` | P2 (stack profile, ADRs), P3 setup, P5 CI and release |
| `references/testing.md` | P2 (test strategy), P3 (unit tests), P4 (full verification) |
| `assets/templates/*.md` | At the start of each phase, copied into `docs/waterfall/` |
| `assets/scaffold/` | P3 setup (`pyproject.tools.toml`, `Makefile`, `tests/conftest.py`, `.pre-commit-config.yaml`); P5 (`ci.yml`, `Dockerfile`, `.dockerignore`) |
