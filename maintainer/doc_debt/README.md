# Documentation debt ledger

Open rows live in [`open.yaml`](open.yaml). Closed rows accumulate in [`resolved.yaml`](resolved.yaml).

[`docs/registry/path_overrides.yaml`](../../docs/registry/path_overrides.yaml) caps how many path-level registry overrides may exist (`override_guard.max_paths`). Raising that cap should be recorded in [`../../reports/decision_log.md`](../../reports/decision_log.md) (same bar as other governance changes).
