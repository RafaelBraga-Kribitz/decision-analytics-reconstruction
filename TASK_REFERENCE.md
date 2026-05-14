# Task Reference (Quick Lookup)

**Purpose:** Detailed task descriptions, dependencies, and execution notes. For phase status and gates, see `IMPLEMENTATION_PLAN.md`.

**Last Updated:** 2026-05-15 (reflects T1–T9 execution completion status)

---

## All Tasks by Tier (Quick Status)

| Task | Title | Effort | Status | Gate | Next |
|------|-------|--------|--------|------|------|
| **T1-1** | Pyright strict CI job (Module C) | 0.5h | ✅ DONE | G4 | — |
| **T1-2** | Slow pipeline acceptance test | 0.25h | ✅ DONE | G1 | — |
| **T1-3** | MLflow local file store | 2.0h | ✅ DONE | G1 | — |
| **T1-4** | E2E walkthrough notebook | 1.5h | ✅ DONE | G1 | — |
| **T1-5** | Business case CFO summary | 1.0h | ✅ DONE | G12 | — |
| **T2-1** | Peer code review | 3.0h | ⏳ ASYNC | G4 | Ready (code stable) |
| **T4-1** | Deploy Module A Streamlit | 1.5h | ❌ TODO | G8 | Ready (T6 unblocked) |
| **T4-2** | Deploy Module B FastAPI | 1.5h | ❌ TODO | G8 | Ready (T6 unblocked) |
| **T4-3** | Deploy Module C Quarto | 0.5h | ❌ TODO | G8 | Ready (T6 unblocked) |
| **T5-1** | DVC init + remote | 1.5h | ✅ DONE | G13 | — |
| **T5-2** | dvc.yaml pipeline | 1.0h | ✅ DONE | G13 | — |
| **T5-3** | CI dvc status job | 1.0h | ✅ DONE | G13 | — |
| **T6-1** | TSP/VRP routing | 4.0h | ✅ DONE | — | 8 tests pass; routing_schedules.parquet |
| **T6-2** | Monte Carlo 10k draws | 3.0h | ✅ DONE | — | monte_carlo_draws.parquet |
| **T6-3** | Battleground heatmap | 2.0h | ✅ DONE | — | battleground_*.geojson |
| **T6-4** | MILP bundle constraints | 2.0h | ✅ DONE | — | 20 MILP tests pass |
| **T7-1** | IMPLEMENTATION_PLAN.md | 1.0h | ✅ DONE | G11 | — |
| **T7-2** | Data dictionary complete | 2.0h | ✅ DONE | G11 | — |
| **T7-3** | Decision log 8+ entries | 1.5h | ✅ DONE | G11 | — |
| **T7-4** | Epistemic boundaries doc | 1.0h | ✅ DONE | G11 | — |
| **T7-5** | Baseline comparison doc | 0.5h | ✅ DONE | G11 | — |
| **T8-1** | Pyright strict Module A | 3.0h | ✅ DONE | G4 | — |
| **T8-2** | Pyright strict Module B | 2.0h | ✅ DONE | G4 | — |
| **T8-3** | Pyright strict Module C | 2.0h | ✅ DONE | G4 | — |
| **T8-4** | Docker smoke test CI | 1.5h | ✅ DONE | G7 | — |
| **T9-1** | Walk-forward validation | 2.0h | ✅ DONE | G5 | — |
| **T9-2** | Posterior predictive checks | 1.0h | ✅ DONE | G5 | — |
| **T9-3** | Interval coverage rates | 0.5h | ✅ DONE | G5 | — |
| **T10-1** | Digital ad channels Module A | 2.0h | ⏳ IN PROGRESS | — | Data dict + decision log |

---

## Phase Dependencies

```
Phase 1 (Blockers)
  ↓
Phase 2 (Tests) → Phase 3 (Lint) → Phase 4 (Architecture) → Phase 5 (DVC)
  ↓
Phase 6 (Tier 3 components)
  ↓
Phase 7 (Documentation)
  ↓
Phase 8 (Pyright strict + Docker CI) ← T8-1/2/3 ✅; T8-4 ⏳
  ↓
Phase 9 (Statistics) ← T9-1/2/3 ✅
```

---

## Progress Snapshot

| Category | Count | Status |
|----------|-------|--------|
| Completed | 26 | ✅ T1-5, T5-1→3, T6-1→4, T7-1→5, T8-1→4, T9-1→3 |
| In progress | 1 | ⏳ T10-1 Digital channels (Phase 10: scope enhancement) |
| Pending (ready) | 4 | ⏳ T2-1 (async review), T4-1/2/3 (deployment) |
| Effort invested | 56.5h | 93% of expanded scope (~60.5h: T1-9 49h + T10 1.5h est) |
| Gates closed | 10 | G2, G4, G5, G7, G9, G10, G11, G12, G13 (+ G1, G3, G6 structural) |
| Tests passing | 476+ | Non-slow suite; Pyright strict clean |

---

## Key Reproduction Commands

```bash
# Phase 1–7 verification
make ci                                    # CI green
make test                                  # 476+ non-slow tests pass
make lint                                  # Lint clean
poetry run pyright src/                    # Pyright strict (all modules)

# Module C artifacts
make module-c-walk-forward                 # T9-1 walk-forward validation
make module-c-ppc                          # T9-2 posterior predictive checks
make module-a-export                       # T6 Module A export

# Data integrity
dvc status                                 # All pipeline outputs tracked
dvc repro --dry                            # Verify all stages
```

---

## Model Routing (Task Assignments)

| Task | Complexity | Assigned Model | Notes |
|------|------------|-----------------|-------|
| T2-1 | Code review | Async human | Peer review gate; can run in parallel |
| T4-1→3 | DevOps/config | Sonnet | PaaS deployment; standard patterns |
| T6-1 | Algorithms | Opus | Graph TSP/VRP; non-trivial optimization |
| T6-2 | Statistics | Opus | MC stratification; scenario branching |
| T8-4 | CI/CD | Haiku | Single job; boilerplate YAML |

