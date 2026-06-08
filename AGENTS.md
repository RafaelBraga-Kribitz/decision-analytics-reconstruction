# Agent Instructions

This repository uses the governance-bootstrap workflow as its single
AI-assisted work protocol.

Start every session with:

```bash
make session-start
```

Then read `governance/SESSION_HANDOUT.md` and follow
`governance/AUDIT_PROCEDURE.md`.

The active work queue is `governance/findings/F-*.yaml`. Work one open finding
at a time, and close a finding only when its `verification_script` exits 0.

Machine and terminology constraints still apply through:

- `.cursor/rules/05-terminology-compliance-gate.mdc`
- `.cursor/rules/06-developer-machine-macpro-6-1.mdc`