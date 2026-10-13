---
name: approve
description: Sign off the waterfall phase (or change request) that is awaiting approval, then continue to the next phase.
disable-model-invocation: true
argument-hint: "[optional note, e.g. 'with the FR-004 wording we discussed']"
---

The user typed `/approve`. This is their explicit sign-off. Note from the user: $ARGUMENTS

1. Read `docs/waterfall/STATUS.md`.
2. Find what is waiting:
   - a phase whose status is `Awaiting approval`, or
   - a change request whose status is `Proposed`.

   If nothing is waiting, tell the user so and stop. If several things are waiting, ask which one they mean and stop.
3. If the note asks for changes ("approve after…", "but…"), the approval is conditional. Make those changes and re-present them. Don't record the approval yet; ask the user to approve the revised version.
4. Otherwise, record the approval with the Edit tool:
   - **Phase:**
     - Set the deliverable's header Status to `Approved`.
     - In STATUS.md, set the phase status to `Approved`, set `Approved on` to today's date, and set `Current phase` to the next phase.
     - Add a sign-off log row: today's date, the phase, and the user's words (`/approve` plus any note).
   - **Change request:** set its status to `Approved` and add a sign-off log row.
5. Continue with the `python-waterfall` skill: start the next phase, or carry out the approved change request.
