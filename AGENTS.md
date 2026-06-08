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

## Graphify (tiered — see `.cursor/rules/graphify.mdc`)

- **Tier 1 (narrow):** grep + read known paths; do not load the graph first.
- **Tier 2 (cross-module / architecture):** `graphify query` or `GRAPH_REPORT.md` summary sections.
- **Tier 3 (session end):** `make graphify` after any session that changed code or configs.