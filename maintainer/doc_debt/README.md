# Documentation debt ledger

Open rows live in [`open.yaml`](open.yaml). Closed rows accumulate in [`resolved.yaml`](resolved.yaml).

[`docs/registry/path_overrides.yaml`](../../docs/registry/path_overrides.yaml) caps how many path-level registry overrides may exist (`override_guard.max_paths`). Raising that cap should be recorded in [`../../reports/decision_log.md`](../../reports/decision_log.md) (same bar as other governance changes).

## 2026-11-02 — preserve portfolio metadata on registry rebuild

The committed registry already contained stable IDs and ownership for the economic evaluation and lessons learned, but their source overrides were missing. The override cap moves from 57 to 59 only to register those two existing metadata contracts. Rebuilding after the README translations must preserve those IDs and must not create new narrative authority. Trilingual README entries derive their provenance from the English README without adding override exceptions (F-032-A).
