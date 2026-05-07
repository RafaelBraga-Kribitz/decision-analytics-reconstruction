# Task taxonomy

Use one **primary** label per task for routing (`/task-intake`).

| Taxonomy | Meaning | Typical primary agent |
|----------|---------|------------------------|
| `infra` | CI, Docker, DVC, Poetry, Makefile, repo layout, GitHub Actions | `integration-impact-auditor` (+ module owner if touching module code) |
| `module_a` | Synthetic population, cleaning, segmentation, propensity, Streamlit | `module-a-specialist` |
| `module_b` | FX, caps, LP/MILP/TSP, allocation outputs, FastAPI | `module-b-specialist` |
| `module_c` | Measurements, Bayesian model, scenarios, Quarto | `module-c-specialist` |
| `cross_module` | Schema/contracts, lineage outputs, or edits spanning A/B/C | Owner by **largest blast radius** + `integration-impact-auditor` |
| `docs_only` | Narrative docs with **no** schema/code/story change | Orchestrator optional; still use `/task-plan` if multi-file |
| `research` | Methods exploration without shipping code | Same domain specialist; narrow scope; may skip CI but **not** skip plan |

## Risk overlay

Add **risk** `low` | `medium` | `high`:
- **high:** calibration anchors, `schema_contracts/**`, solver/API contracts, PyMC priors/diagnostics, terminology-facing releases
- **medium:** new tests/features within one module
- **low:** typos, comments, single-doc clarification

**high** → always involve `qa-gatekeeper` before `/task-complete`.
