---
name: project-verification
description: Evidence-gated verification for all PARAGUAY_ELLECTION tasks. Embeds verification-before-completion gate function, 6-layer QA, and signed-verdict format. Use before every /task-verify and /task-complete.
disable-model-invocation: true
---

# Project verification

## Non-negotiable verification gate function

```
1. IDENTIFY  — state the exact command that proves the claim
2. RUN       — execute it fresh, fully, in this session
3. READ      — read full output; check exit code; count failures/passes
4. VERIFY    — does output confirm the claim?
             → If NO:  state actual status with evidence; halt; do not complete
             → If YES: paste relevant output as evidence
5. ONLY THEN — write completion claim
```

Never use: "should pass", "probably", "I'm confident", "I manually verified". These are not evidence.

## Proof shape for `/task-verify`

Every criterion row in the task plan must map to exactly one evidence entry:

```
| Criterion | Verification command | Exit / result | Pass/Fail |
|-----------|---------------------|---------------|-----------|
| <from plan> | <exact cmd> | <0 / PASS / numeric value> | PASS |
```

No blank rows. No "see above". No "✓" without numeric backing.

## Proof shapes by module

**Module A:**
- `pytest tests/module_a/ -v` → exit 0, show N/N pass
- Gate A1: paste `validator.py` output showing all anchors within tolerance
- Gate A5/A6: paste silhouette + ARI numeric values
- Gate A7/A8/A9: paste Brier score and demographic mean propensities

**Module B:**
- `pytest tests/module_b/ -v` → exit 0
- Gate B1: paste solver status line
- Gate B2: paste `total_allocated / total_budget_pyg = X.XXXX` (≤ 1.001)
- Gate B3: paste `municipalities_covered / total_municipalities = X.XX%` (≥ 80%)
- Gate B9: paste p95 latency from FastAPI test

**Module C:**
- `pytest tests/module_c/ -v` → exit 0
- Gate C1–C3: paste `az.summary()` R-hat and ESS columns; paste divergence count
- Gate C6: paste national scenario mean ± HDI
- Gate C11: paste `quarto render` exit 0 line

## No-close rule

`/task-complete` is BLOCKED unless:
1. Verification gate function was executed in this session (not a prior session).
2. All criterion rows in the plan have evidence in the proof shape table.
3. qa-gatekeeper signed verdict is attached (for medium/high risk tasks).
4. Zero open blocking issues in the QA report.

## Global skill chain

1. `verification-before-completion` — gate function (apply first, always).
2. `systematic-debugging` — if any check fails, 4 phases before proposing fix.
3. `test-driven-development` — confirm TDD cycle was followed; if not, task cannot be marked complete.
