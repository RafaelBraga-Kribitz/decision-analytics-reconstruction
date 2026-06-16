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
| `numeric_drift` | Same constant declared in multiple places without single-source enforcement; or any magic value hardcoded in src/scripts/notebooks that belongs in config/ |
| `unverifiable_navigation_claim` | Claim about agent / IDE behavior with no on-disk evidence |
| `missing_artifact` | A referenced artifact (chart, report, notebook output) does not exist |
| `claim_without_evidence` | A claim in README / Charter has no traceable source |
| `coverage_regression` | Test line or branch coverage drops below the threshold in `config/quality_gates.yaml` |
| `complexity_violation` | A function's cyclomatic complexity exceeds `max_per_function` in `config/quality_gates.yaml` |
| `module_size_violation` | A source file or function exceeds the line-count budget in `config/quality_gates.yaml` |
| `dependency_violation` | A module imports from a layer it is not permitted to depend on per `.importlinter` rules |
| `crap_violation` | A function's CRAP score (C²·(1−COV)³+C) exceeds `max_score` in `config/quality_gates.yaml` |
| `mutation_weakness` | Mutation score drops below threshold — file manually after running `mutmut`; not gated in CI |
| `notebook_drift` | Hardcoded magic value found inside a Jupyter notebook code cell |
| `sql_drift` | Hardcoded threshold / date / interval found in a `.sql` or `.sql.j2` file |
| `registry_incomplete` | `parameter_registry.yaml` missing entries, orphan config keys, or unresolved `config.X` references in code |
| `feature_flag_drift` | Feature flag referenced in code but missing from `config/features.yaml`; or commented-out code acting as a de-facto flag (manual filing, no CI gate) |

If a real-world drift doesn't fit any row, file a meta-finding `F-METHODOLOGY-DRIFT-NNN` proposing the new category. **Do not silently invent slugs in F-*.yaml files** — `scripts/write_audit_state.py` will accept them but the category list becomes unenforceable.

---

## SSOT Hierarchy (enforced by `scripts/check_hardcoded_values.py`)

Every project bootstrapped from this kit must obey the Single Source of Truth hierarchy. Violations are filed as `numeric_drift`.

```
config/parameter_registry.yaml   ← owner + rationale + change history
        ↓
config/*.yaml                    ← value declarations (global, modeling,
        ↓                           business_rules, visualization, paths)
src / scripts / notebooks        ← code reads config; never re-declares literals
        ↓
charts / reports / dashboards    ← outputs derive from code; never hard-assert numbers
```

### Allowed in code

| Pattern | Reason |
|---|---|
| `config.random_seed` | SSOT reference |
| `0`, `1`, `-1`, `2` | Trivial / loop-related |
| `np.pi`, `math.e` | Mathematical constants |
| Values inside `config/` or `tests/` | SSOT declaration or test fixture |

### Forbidden in code (file as `numeric_drift`)

| Pattern | Why forbidden |
|---|---|
| `random_state = 42` in training.py | Duplicate of `config/global.yaml` |
| `TEST_SIZE = 0.2` in evaluation.py | Duplicate of `config/modeling.yaml` |
| `if revenue > 10000:` without config ref | Unexplained business rule |
| `last_purchase_date >= current_date - 90` hardcoded | Must be `config.active_customer_days` |
| `DATE_START = "2024-01-01"` in src/ | Must be `config/business_rules.yaml` |

### Parameter Registry rule

Every entry in `config/*.yaml` **must** appear in `config/parameter_registry.yaml` with:

- `value` — the current value
- `source_file` — which config YAML owns it
- `owner` — team or person accountable for the value
- `rationale` — WHY this value (not what it is)
- `history[]` — append-only change log

A parameter without a registry entry is an undocumented assumption. File a `numeric_drift` finding.
