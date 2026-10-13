---
paths:
  - "docs/waterfall/**"
---

# Phase documents

- Each document starts from its template in `.claude/skills/python-waterfall/assets/templates/`. Keep the template's sections and ID conventions.
- **The STATUS.md layout is machine-read** by `.claude/hooks/`:
  - Keep the Phases table's columns and order (`Phase | Deliverable | Status | Approved on | Notes`), one row per phase.
  - Keep the `## Phases` and `## Change requests` headings, and the `Current phase`, `Project status` and `Gate policy` rows.
  - Use only these phase status values: `Not started`, `In progress`, `Awaiting approval`, `Approved`, `Approved (gate waived)`.
  - Use only these CR status values: `Proposed`, `Approved`, `Rejected`, `Implemented`.
- Edit STATUS.md with the Edit tool, not the shell. Marking a phase or CR approved is blocked unless the user approved it in this turn.
- Changing an approved document needs an approved CR. Bump the document's version, add a changelog line citing the CR, then update everything downstream that it affects.
- No leftover placeholders (`<…>`, `TBD`). A section that doesn't apply says `N/A — <reason>`.
- Be concise and concrete: tables and bullets, real names, real code for models. Every requirement is testable and every NFR is measurable.
