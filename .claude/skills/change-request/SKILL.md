---
name: change-request
description: Open a waterfall change request (CR) for a change to approved requirements, design, code or stack — with an impact analysis — and wait for the user's approval.
disable-model-invocation: true
argument-hint: "[what should change and why]"
---

The user wants to change something that's already baselined: $ARGUMENTS

Follow the change-request rule of the `python-waterfall` skill.

1. Read `docs/waterfall/STATUS.md` and the approved phase documents. If the request is unclear, ask one round of clarifying questions first.
2. Analyse the impact. Find every affected item:
   - requirement IDs (new, changed or withdrawn FR/NFR/AC)
   - design sections, ADRs, models and interface contracts (CLI commands, endpoints, public API)
   - source files and tests: `grep -rn "<ID>" src tests docs/waterfall`
   - dependencies (`pyproject.toml`) and migrations, if any
   - RTM rows
   - phases that need re-verification. A change to code after P4 means re-running the affected tests (and `make rtm`).
3. Take the next free `CR-###` number. Add a row to the Change requests table with today's date, the change and its reason, what it affects, and status `Proposed`.
4. Present the CR to the user:
   - what changes and why
   - the impact list
   - the effort and the risk
   - any alternative, such as deferring it to a later version

   Then ask them to reply **approve** (or use `/approve`) or to reject it. End your turn.
5. Do nothing else until the user approves. On approval, update the upstream document first (bump its version and add a changelog line citing the CR). Then ripple downstream: design → code → tests → RTM. Set the CR to `Implemented` once everything it affects is updated and verified.
