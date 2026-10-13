# Waterfall process (always applies)

- All feature work in this repo goes through the `python-waterfall` skill. `docs/waterfall/STATUS.md` is the source of truth for the current phase. Read it before doing anything else.
- Phases run strictly in order: Requirements → Design → Implementation → Testing → Deployment → Maintenance. Never start a phase before the previous one is approved.
- Record an approval only when the user has explicitly approved, in their own words ("approve", "LGTM", "go ahead") or with `/approve`. Log those words in the sign-off table. Never infer approval from silence, feedback, a question or a conditional reply.
- Approved documents are baselined. Changing behaviour, scope, design, data model, interface contracts or the stack requires a change request (`CR-###` in STATUS.md) that the user approves first. The `/change-request` command starts one.
- IDs are permanent: `FR-###`, `NFR-###`, `AC-###.#`, `ADR-###`, `DEF-###`, `CR-###`. Tests carry the IDs they verify with `@pytest.mark.req(...)`.
- Hooks enforce the gates:
  - no application code, project config or installs before Design is approved
  - no CI or deploy config before Testing is approved
  - STATUS.md can mark an item approved only in the turn the user approved it
  - nothing may wipe `docs/waterfall/`

  If a hook blocks you, the block is the process working. Finish the phase or ask the user. Never edit STATUS.md, the hooks or the settings to get around a gate. Only the user may set `WATERFALL_GATE=off`.
- Before presenting a phase gate, run the `phase-reviewer` agent on the deliverable and fix its blocking findings.
- Never fabricate results. Test output, coverage, benchmarks, audit results and deploy status must come from commands that actually ran.
