---
name: waterfall-status
description: Show where the waterfall project stands — current phase, sign-offs, pending approval, open change requests and the next action.
disable-model-invocation: true
allowed-tools: Read Glob Grep
---

Report the status of this waterfall project. Don't change any files.

1. Read `docs/waterfall/STATUS.md`. If it doesn't exist, say that no waterfall project has started yet. Suggest describing the software to build (for example, "Build a CLI that tracks my expenses, using the waterfall process") and stop.
2. Otherwise, reply with:
   - a table of the six phases with status and approval date
   - the phase currently in progress or awaiting approval, with a link to its document
   - open change requests (any status other than Implemented or Rejected), with a one-line summary each
   - open questions from the current phase's document, if any
   - **Next action:** one sentence saying what the user needs to do (approve, answer questions, review a CR) or what Claude will do next.

Keep it under 25 lines.
