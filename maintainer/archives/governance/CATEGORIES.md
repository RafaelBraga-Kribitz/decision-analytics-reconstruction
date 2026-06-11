# Finding Categories

These are the only sanctioned category slugs for `governance/findings/F-*.yaml`. Adding a new slug requires an ADR.

| Slug | When to use |
|---|---|
| `documentation_entropy` | Docs grow, contradict each other, or drift from code |
| `charter_sprawl` | PROJECT_CHARTER.md grows past its line budget |
| `fake_completion` | A feature is claimed done but lacks a verification artifact |
| `partial_migration` | Old + new code paths coexist with no sunset date |
| `dead_artifacts` | Dead code / unused exports / stale fixtures |
| `stale_generated_outputs` | Reports / charts / notebooks regenerated from sources but committed stale |
| `fragmented_standards` | Two configs disagree (e.g., pyright "strict" claimed but "basic" set) |
| `orphaned_workflows` | CI workflow exists but never gates a PR |
| `governance_gaps` | Governance scope misses a canonical path |
| `cross_session_amnesia` | State must be re-derived from chat history rather than disk |
| `methodology_drift` | A new audit framework is being invented |
| `audit_doc_accumulation` | Audit / journal docs accumulate with no retirement rule |
| `fake_pre_commit` | Pre-commit config exists but hooks aren't installed locally / in CI |
| `numeric_drift` | Same constant declared in multiple places without single-source enforcement |
| `unverifiable_navigation_claim` | Claim about agent / IDE behavior with no on-disk evidence |
| `missing_artifact` | A referenced artifact (chart, report, notebook output) does not exist |
| `claim_without_evidence` | A claim in README / Charter has no traceable source |

If a real-world drift doesn't fit any row, file a meta-finding `F-METHODOLOGY-DRIFT-NNN` proposing the new category. **Do not silently invent slugs in F-*.yaml files** — `scripts/write_audit_state.py` will accept them but the category list becomes unenforceable.

## Debt-scanner → category mapping

The debt ratchet (`scripts/debt_scan.py`) measures metrics that map onto these categories. When you promote a debt hotspot from the session handout into a formal finding, use the matching slug:

| Debt metric | Category slug |
|---|---|
| `ruff_unused`, `knip_unused_*` | `dead_artifacts` |
| `vulture_dead_code`, `fallow_dead_code` | `dead_artifacts` |
| `jscpd_duplication_pct`, `fallow_duplication_pct` | `partial_migration` (copy-paste drift) |
| `radon_complex_blocks` | `fragmented_standards` (complexity beyond agreed cap) |

The metric value gives you the `evidence`; the tool re-run scoped to the fixed area is the `verification_script`.
