Good. I have confirmed new bugs. All findings below are genuinely new. Nothing repeats the previous two audits. Every prompt is copy-paste ready for Claude Code.

---

# New Full Audit — Net-New Issues Only

All 10 phases below are additive to the previous audit. Execute after completing that queue.

---

## PHASE N1: Runtime Crashes Not in Previous Audit

---

### N1.1 — KMeans `n_jobs` parameter does not exist in scikit-learn 1.4
**Severity: P0**

Confirmed: `KMeans.__init__` in sklearn 1.4 accepts: `n_clusters, init, n_init, max_iter, tol, verbose, random_state, copy_x, algorithm`. `n_jobs` was removed in sklearn 0.25. `model_params.yaml` passes `n_jobs: -1` to KMeans. Any code that reads this config and passes it as `**kwargs` to `KMeans()` will raise `TypeError: __init__() got an unexpected keyword argument 'n_jobs'`.

```
Fix the invalid KMeans n_jobs parameter in model_params.yaml and document the removal.

1. In module_a_population_segmentation/config/model_params.yaml, under the kmeans section:
   REMOVE the line:  n_jobs: -1
   ADD a comment where it was:
     # n_jobs removed: KMeans parallelism in sklearn >= 0.25 is controlled by
     # OpenMP thread count via the OMP_NUM_THREADS environment variable.
     # Set OMP_NUM_THREADS=8 in .env for multi-core acceleration.

2. KEEP n_jobs: -1 in the dbscan section — DBSCAN does support n_jobs.

3. In .env.example, add:
   # ─── Parallelism ─────────────────────────────────────────────────────────
   OMP_NUM_THREADS=4   # Controls KMeans OpenMP threads; set to CPU core count

4. In models/segmentation.py (to be implemented), when constructing KMeans:
   - Read only the params that KMeans actually accepts from config
   - Use an explicit allowlist:
     KMEANS_VALID_PARAMS = {"n_clusters", "init", "n_init", "max_iter", 
                             "tol", "random_state", "copy_x", "algorithm"}
   - Filter config before passing:
     kmeans_kwargs = {k: v for k, v in kmeans_cfg.items() if k in KMEANS_VALID_PARAMS}
   - Log any filtered keys at WARNING level

5. Add a test in test_segmentation.py:
   def test_kmeans_instantiates_without_error(config):
       from population_segmentation.models.segmentation import KMeansSegmenter
       # Should not raise TypeError for unknown params
       segmenter = KMeansSegmenter(config)
       assert segmenter is not None
```

---

### N1.2 — CI uses `poetry install --no-root` — all test imports fail silently
**Severity: P0**

Confirmed: `poetry install --no-root` installs all dependencies but does NOT install the root package (`population_segmentation`). Every test file starts with `from population_segmentation.data.generator import generate_population`. This import fails in CI with `ModuleNotFoundError`. The CI pipeline shows green on lint/typecheck (which don't import the package) but every pytest test would fail with ModuleNotFoundError. This means the CI coverage badge is meaningless.

```
Fix .github/workflows/ci.yml: replace poetry install --no-root with poetry install.

1. In .github/workflows/ci.yml, find the step:
   - name: Install dependencies
     run: poetry install --no-root

   Change to:
   - name: Install dependencies
     run: poetry install

2. Explain why: --no-root skips installing the population_segmentation package itself.
   Without it, `from population_segmentation.data.generator import ...` raises
   ModuleNotFoundError in all test files.

3. Add a verification step immediately after Install dependencies:
   - name: Verify package importable
     run: |
       poetry run python -c "import population_segmentation; print('Package import OK')"
       poetry run python -c "from population_segmentation.data.generator import generate_population; print('Generator import OK')"
       poetry run python -c "from population_segmentation.utils.seeds import make_rng; print('Seeds import OK')"

4. If poetry install fails due to platform/OS dependency issues (e.g., pyarrow wheels),
   add a matrix strategy:
   strategy:
     matrix:
       python-version: ["3.11"]
   and reference ${{ matrix.python-version }} in the setup-python step.

Run the full CI pipeline locally to verify:
  poetry install
  poetry run pytest module_a_population_segmentation/tests/ -v
```

---

### N1.3 — `rural_inet` is defined but never used; `whatsapp_pen` uses a hardcoded magic computation instead
**Severity: P1**

In `generator.py`, lines defining the variables:
```python
urban_inet = float(ict.get("whatsapp_urban", 0.74))
rural_inet = float(ict.get("whatsapp_rural", 0.31))
```
Then:
```python
whatsapp_pen = np.where(rural_flags, urban_inet * 0.42, urban_inet).astype(np.float32)
```
`rural_inet` is NEVER REFERENCED after assignment. `urban_inet * 0.42 = 0.74 * 0.42 = 0.3108`, which happens to approximate `rural_inet = 0.31` by coincidence. This introduces a magic number (0.42), makes the rural penetration undocumented, and makes `rural_inet` a dead variable that ruff will flag as F841.

```
Fix the rural_inet unused variable and whatsapp_pen magic computation in
module_a_population_segmentation/src/population_segmentation/data/generator.py.

1. Find this block (approximately line 160-165):
   ict = config.get("media_penetration_defaults", {})
   urban_inet = float(ict.get("whatsapp_urban", 0.74))
   rural_inet = float(ict.get("whatsapp_rural", 0.31))
   # Approximate internet access from ICT anchors
   inet_prob = np.where(rural_flags, 0.279, 0.734)
   internet_access_flags = rng.random(n) < inet_prob

2. And this block (approximately line 170-172):
   whatsapp_pen = np.where(rural_flags, urban_inet * 0.42, urban_inet).astype(np.float32)

3. Replace both blocks with:
   ict_cfg = config.get("media_penetration_defaults", {})
   whatsapp_urban_penetration = float(ict_cfg.get("whatsapp_urban", 0.74))
   whatsapp_rural_penetration = float(ict_cfg.get("whatsapp_rural", 0.31))
   internet_urban_penetration = 0.734   # DGEEC ICT survey ~2018; matches calibration_anchors.yaml
   internet_rural_penetration = 0.279   # DGEEC ICT survey ~2018; matches calibration_anchors.yaml
   
   inet_prob = np.where(rural_flags, internet_rural_penetration, internet_urban_penetration)
   internet_access_flags = rng.random(n) < inet_prob
   
   # WhatsApp penetration: distinct from general internet access
   # Rural penetration driven by smartphone ownership, not just connectivity
   whatsapp_pen = np.where(
       rural_flags,
       whatsapp_rural_penetration,
       whatsapp_urban_penetration,
   ).astype(np.float32)

4. Move internet_urban_penetration and internet_rural_penetration into the
   generation.yaml config (they are currently hardcoded as 0.734 and 0.279):
   Add to generation.yaml under a new key:
   internet_penetration:
     urban: 0.734   # [VERIFIED band — DGEEC ICT survey ~2018] ±2 pp
     rural: 0.279   # [VERIFIED band — DGEEC ICT survey ~2018] ±2 pp

5. Update generator.py to read from config:
   inet_cfg = config.get("internet_penetration", {})
   internet_urban_penetration = float(inet_cfg.get("urban", 0.734))
   internet_rural_penetration = float(inet_cfg.get("rural", 0.279))

6. Run: poetry run ruff check module_a_population_segmentation/src
   Confirm F841 (local variable is assigned but never used) is resolved for rural_inet.

7. Run: poetry run pytest module_a_population_segmentation/tests/test_generator.py
   -k "test_urban_rural_approximate" -v to confirm the fix doesn't break calibration.
```

---

### N1.4 — `max_noise_rate` value and comment are contradictory in model_params.yaml
**Severity: P1**

```yaml
max_noise_rate: 0.01  # Gate A4: raise error if noise_rate > 0.03
```

The value is 0.01 but the comment says 0.03. The QA gate will fire at noise_rate > 0.01, not > 0.03. Any implementation that reads this config and uses the comment as specification will implement the wrong gate.

```
Fix the max_noise_rate inconsistency in 
module_a_population_segmentation/config/model_params.yaml.

Decision required: choose ONE of these two correct forms:

OPTION A — if the intended threshold is 0.01 (strict):
  max_noise_rate: 0.01  # Gate A4: raise QAGateFailure if noise_rate > 0.01
  # Rationale: DBSCAN noise > 1% indicates eps is too small or features are
  # poorly scaled; re-tune before proceeding to K-Means.

OPTION B — if the intended threshold is 0.03 (lenient):
  max_noise_rate: 0.03  # Gate A4: raise QAGateFailure if noise_rate > 0.03
  # Rationale: Up to 3% noise is acceptable for a pre-pass filter;
  # noise points are excluded from K-Means but not from the final output.

The correct answer based on scope_module_A §7.1 is: 0.01 (strict), which prevents
feeding a degraded feature space to K-Means. Use OPTION A.

After choosing, add a sibling key that records what the gate failure message should say:
  max_noise_rate: 0.01
  max_noise_rate_gate_message: >
    DBSCAN noise rate {observed:.3f} exceeds threshold {threshold:.3f}.
    Check: (1) eps parameter, (2) feature scaling, (3) outlier injection in raw layer.

In models/segmentation.py, when implementing the noise gate:
  if noise_rate > config["dbscan"]["max_noise_rate"]:
      raise QAGateFailure(
          gate_name="A4_dbscan_noise_rate",
          expected=config["dbscan"]["max_noise_rate"],
          observed=noise_rate,
          tolerance=0.0,
      )
```

---

## PHASE N2: Makefile and Virtualenv Issues

---

### N2.1 — Makefile bypasses Poetry virtualenv on all targets
**Severity: P1**

```makefile
PYTHON := python3.11
test:
    pytest $(MODULE_A_TESTS) -v --tb=short
coverage:
    pytest $(MODULE_A_TESTS) --cov=...
```

`PYTHON := python3.11` calls the system Python, not the Poetry virtualenv. `pytest` without `poetry run` uses whatever pytest is on PATH, not the project's version. Anyone running `make test` without activating the Poetry virtualenv manually will get wrong Python version, wrong library versions, and import failures.

```
Rewrite the Makefile to use Poetry for all execution targets.

Replace the current Makefile entirely with the following version:

.PHONY: install lint format typecheck test coverage ci all clean generate-dev pipeline-dev dashboard

MODULE_A_SRC := module_a_population_segmentation/src
MODULE_A_TESTS := module_a_population_segmentation/tests

# ─── Environment check ───────────────────────────────────────────────────────
.check-poetry:
	@command -v poetry >/dev/null 2>&1 || { echo "Poetry not found. Install: curl -sSL https://install.python-poetry.org | python3 -"; exit 1; }

install: .check-poetry
	poetry install

# ─── Code quality ─────────────────────────────────────────────────────────────
format: install
	poetry run black $(MODULE_A_SRC) $(MODULE_A_TESTS)

lint: install
	poetry run ruff check $(MODULE_A_SRC) $(MODULE_A_TESTS)
	poetry run black --check $(MODULE_A_SRC) $(MODULE_A_TESTS)

typecheck: install
	poetry run pyright $(MODULE_A_SRC)

# ─── Testing ──────────────────────────────────────────────────────────────────
test: install
	poetry run pytest $(MODULE_A_TESTS) -v --tb=short

coverage: install
	poetry run pytest $(MODULE_A_TESTS) \
		--cov=$(MODULE_A_SRC) \
		--cov-report=term-missing \
		--cov-report=xml \
		--cov-fail-under=80

ci: lint typecheck coverage

all: install ci

# ─── Data pipeline ─────────────────────────────────────────────────────────────
generate-dev: install
	poetry run python -m population_segmentation.data.generator \
		--config module_a_population_segmentation/config/generation.yaml \
		--sample-size 10000 \
		--output data/interim/population_master_raw.parquet

# Note: pipeline-dev requires cleaner.py to be implemented first
pipeline-dev: install
	@echo "Step 1/2: Generate raw population..."
	poetry run python -m population_segmentation.data.generator \
		--config module_a_population_segmentation/config/generation.yaml \
		--output data/interim/population_master_raw.parquet
	@echo "Step 2/2: Clean population..."
	poetry run python -m population_segmentation.data.cleaner \
		--input data/interim/population_master_raw.parquet \
		--output data/processed/population_master_clean.parquet \
		--config module_a_population_segmentation/config/generation.yaml
	@echo "Pipeline complete."

# ─── Dashboard ────────────────────────────────────────────────────────────────
dashboard: install
	poetry run streamlit run module_a_population_segmentation/app/streamlit_dashboard.py

# ─── Setup ────────────────────────────────────────────────────────────────────
# Create required directories (run once after clone)
setup-dirs:
	mkdir -p data/raw data/interim data/processed
	mkdir -p mlflow/mlruns
	mkdir -p module_a_population_segmentation/app
	mkdir -p module_a_population_segmentation/docker
	mkdir -p module_a_population_segmentation/notebooks
	mkdir -p module_b_resource_allocation
	mkdir -p module_c_forecasting_scenarios
	mkdir -p reports
	@echo "Directory structure created."

# ─── Cleanup ──────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov coverage.xml .coverage

After replacing the Makefile, run: make install && make test
to confirm the full chain works.
```

---

### N2.2 — `data/`, `mlflow/`, module B and C directories don't exist; Makefile has no setup target
**Severity: P1**

Fresh clone → `make generate-dev` → fails immediately with `FileNotFoundError: [Errno 2] No such file or directory: 'data/interim/population_master_raw.parquet'` because `data/interim/` doesn't exist. Same for `mlflow/mlruns/`. `module_b_resource_allocation/` and `module_c_forecasting_scenarios/` are referenced in the README module table but no directory exists at all.

```
Create the required directory structure and placeholder files.

Run these commands to establish the scaffold:

# Create data directories with .gitkeep to preserve structure in git
mkdir -p data/raw data/interim data/processed
touch data/raw/.gitkeep data/interim/.gitkeep data/processed/.gitkeep

# Create MLflow directory
mkdir -p mlflow/mlruns
touch mlflow/mlruns/.gitkeep

# Create Module B scaffold
mkdir -p module_b_resource_allocation/src/resource_allocation
mkdir -p module_b_resource_allocation/tests
mkdir -p module_b_resource_allocation/config
mkdir -p module_b_resource_allocation/notebooks
touch module_b_resource_allocation/__init__.py
touch module_b_resource_allocation/src/resource_allocation/__init__.py
touch module_b_resource_allocation/tests/__init__.py

# Create Module C scaffold  
mkdir -p module_c_forecasting_scenarios/src/forecasting
mkdir -p module_c_forecasting_scenarios/tests
mkdir -p module_c_forecasting_scenarios/config
mkdir -p module_c_forecasting_scenarios/notebooks
touch module_c_forecasting_scenarios/__init__.py
touch module_c_forecasting_scenarios/src/forecasting/__init__.py
touch module_c_forecasting_scenarios/tests/__init__.py

# Create Module A missing directories
mkdir -p module_a_population_segmentation/app
mkdir -p module_a_population_segmentation/docker
mkdir -p module_a_population_segmentation/notebooks

# Create Module B README
cat > module_b_resource_allocation/README.md << 'EOF'
# Module B — Resource Allocation Engine

**Status: Specification complete. Implementation in progress.**

This module implements constrained LP optimization allocating a limited budget
across 18 geographic units and 11 channel types to maximize expected participation
rate per monetary unit.

## Implementation plan

See `SPECIFICATION.md` for the full LP formulation, diminishing returns model,
and sensitivity analysis requirements.

## Consumed inputs (from Module A)
- `population_master_clean.parquet`
- `segment_labels.parquet`
- `participation_propensity.parquet`
- `media_reachability_by_segment.csv`

## Produced outputs
- `budget_allocation_weekly.csv`
- `routing_schedules.parquet`
- `reallocation_counterfactuals.parquet`
EOF

# Create Module C README
cat > module_c_forecasting_scenarios/README.md << 'EOF'
# Module C — Probabilistic Forecasting

**Status: Methodology reference complete. Implementation planned.**

See `METHODOLOGY.md` for the full Bayesian hierarchical aggregator specification,
house effect model priors, and synthetic validation traces.
EOF

# Update .gitignore to keep .gitkeep files
# Add this line at the top of the Data section:
# !**/.gitkeep

After running, commit the scaffold:
git add data/raw/.gitkeep data/interim/.gitkeep data/processed/.gitkeep
git add mlflow/mlruns/.gitkeep
git add module_b_resource_allocation/ module_c_forecasting_scenarios/
git add module_a_population_segmentation/app/ module_a_population_segmentation/docker/
git commit -m "scaffold: create required directory structure and module placeholders"
```

---

## PHASE N3: Documentation Integrity

---

### N3.1 — `transformation_log.md` makes a false implementation claim
**Severity: P1**

The first line of the table in `transformation_log.md` states:
> "All steps implemented in `module_a_population_segmentation/src/population_segmentation/data/cleaner.py`."

This file does not exist. Any recruiter or interviewer who reads the transformation log and then looks for the file will find nothing. This is worse than a missing file — it is a falsified claim.

```
Fix reports/transformation_log.md to accurately represent implementation status.

1. Replace the header sentence:
   FROM:
   "All steps implemented in `module_a_population_segmentation/src/population_segmentation/data/cleaner.py`."
   
   TO:
   "Specification: All 14 steps are fully specified below and serve as the
   implementation contract for `cleaner.py`. Implementation status is tracked
   per step in the Status column."

2. Add a Status column to the table with these values:
   | Step | Operation | Rationale | QA checkpoint | Status |
   
   Step 1: Specified
   Step 2: Specified
   Step 3: Specified
   Step 4: Specified
   Step 5: Specified
   Step 6: Specified
   Step 7: Specified
   Step 8: Specified
   Step 9: Specified
   Step 10: Specified
   Step 11: Specified
   Step 12: Specified
   Step 13: Specified
   Step 14: Specified

3. Add a banner at the top of the file:
   > **Implementation Status:** cleaner.py is not yet implemented.
   > This document is the authoritative specification. Every step below has
   > a corresponding QA gate that will be enforced at runtime.
   > See [ROADMAP.md](../ROADMAP.md) for timeline.

4. Create ROADMAP.md in the repo root with this content:

# Implementation Roadmap

## Current status (as of 2026-05-12)

| Component | Status | Blocking |
|---|---|---|
| generator.py | Complete | No |
| raw_injector.py | Complete (1 bug fix pending) | No |
| cleaner.py | Not started | Dashboard |
| features/engineer.py | Not started | Models |
| models/segmentation.py | Not started | Dashboard |
| models/propensity.py | Not started | Dashboard |
| evaluation/validator.py | Not started | CI |
| app/streamlit_dashboard.py | Not started | Portfolio launch |
| Module B LP optimizer | Not started | Portfolio launch |
| Module C Bayesian aggregator | Methodology only | — |

## Next sprint priorities (for portfolio launch)
1. cleaner.py (14 steps, all specified in transformation_log.md)
2. features/engineer.py (13 engineered features, all specified in model_params.yaml)
3. models/propensity.py + models/segmentation.py
4. app/streamlit_dashboard.py + Render deployment
5. reports/case_study_business.pdf (6-slide PDF)

## Portfolio launch gate
The portfolio goes public only when:
- Module A pipeline runs end-to-end: make pipeline-dev succeeds
- Dashboard is deployed and accessible at the Render URL
- case_study_business.pdf exists and is ≤ 6 slides
- CI badge is green
```

---

### N3.2 — `IMPLEMENTATION_PLAN.md` is linked in README but does not exist
**Severity: P1**

```
Create IMPLEMENTATION_PLAN.md in the repository root.

This file is listed in the README repository structure as:
  "IMPLEMENTATION_PLAN.md  ← engineering reviewer entry point"

It must exist. A reviewer who looks for it finds a 404.

Content requirements:

# Implementation Plan

## Engineering reviewer: start here

This document describes the engineering decisions, implementation sequence,
and technical standards applied in this reconstruction.

## Implementation sequence rationale

The implementation follows a strict dependency chain:
1. generator.py → raw_injector.py → cleaner.py: data must flow before models train
2. features/engineer.py: depends on clean data schema
3. models/segmentation.py + propensity.py: depend on feature matrix
4. evaluation/validator.py: depends on model output schema
5. app/streamlit_dashboard.py: depends on all of the above

## Technical decisions

All non-trivial decisions are logged in reports/decision_log.md.
Key decisions:
- K-Means with k=6 (operational requirement from Module B)
- Logistic regression + Platt calibration (interpretability + exact SHAP)
- Synthetic data generation (legal + privacy; see decision_log.md entry)
- Schema-first design (schema_contracts/ validated at runtime by validator.py)

## Quality gates

Each pipeline stage must pass its QA gate before downstream stages can run.
Gates are implemented in evaluation/validator.py and raise QAGateFailure.
The full gate list with thresholds is in model_params.yaml.

## Reproducibility standards

- All randomness: seeded via RANDOM_SEED env var (default: 42)
- All data: versioned via DVC (configuration in .dvc/)
- All experiments: tracked via MLflow (tracking URI: ./mlflow/mlruns)
- All dependencies: pinned via poetry.lock

## How to run

See Makefile for all executable targets. Start with:
  make install      # install all dependencies
  make test         # run all tests
  make generate-dev # generate 10k synthetic entities
  make dashboard    # launch Streamlit dashboard (requires cleaner + models)

## Current implementation gap

See ROADMAP.md for honest status of what is and is not implemented.
```

---

## PHASE N4: Performance and Correctness at Scale

---

### N4.1 — `_rake_categorical` allocates full index arrays per donor; memory-intensive at 4.26M
**Severity: P2**

The current implementation calls `np.where(arr == donor)[0]` to get all indices for a label, then `rng.choice(full_index, size=to_move, replace=False)`. At N=4.26M, a single label's index array contains ~1.4M int64 values (11MB). Four labels × four potential passes = 44MB+ of temporary allocations per rake call. At the cleaner step 11 (language raking), this is called once. At full production scale this is acceptable but tight.

```
Optimize _rake_categorical in 
module_a_population_segmentation/src/population_segmentation/data/generator.py
for memory efficiency at N=4.26M scale.

Replace the current _rake_categorical function with this optimized version:

def _rake_categorical(
    arr: np.ndarray,
    targets: dict[str, float],
    rng: np.random.Generator,
) -> np.ndarray:
    """Rake a categorical array to target marginal proportions.
    
    Uses index-based raking: builds a sorted permutation of source indices,
    then reassigns labels by slicing — O(n) memory, O(n log n) time.
    
    Args:
        arr: Input categorical array (object dtype).
        targets: Target proportions for each category. Must sum to 1.0.
        rng: Seeded numpy Generator.
    
    Returns:
        Modified array with adjusted category proportions.
    """
    arr = arr.copy()
    n = len(arr)
    labels = list(targets.keys())
    
    # Compute target counts; adjust first label for rounding residual
    target_counts = {k: int(round(v * n)) for k, v in targets.items()}
    delta = n - sum(target_counts.values())
    if delta != 0:
        target_counts[labels[0]] += delta
    
    # Compute current counts
    current_counts = {k: int((arr == k).sum()) for k in labels}
    
    # Build donor pool: all indices that are over-represented
    surplus_indices: list[np.ndarray] = []
    surplus_labels: list[str] = []
    for label in labels:
        excess = current_counts.get(label, 0) - target_counts[label]
        if excess > 0:
            all_idx = np.where(arr == label)[0]
            # Shuffle to avoid systematic bias in which rows are relocated
            rng.shuffle(all_idx)
            surplus_indices.append(all_idx[:excess])
            surplus_labels.extend([label] * excess)  # not needed; indices sufficient
    
    if not surplus_indices:
        return arr  # Already at target; nothing to do
    
    # Single concatenation of all surplus indices
    donor_pool = np.concatenate(surplus_indices)
    
    # Assign new labels to donor pool based on deficit
    deficit_labels: list[str] = []
    for label in labels:
        deficit = target_counts[label] - current_counts.get(label, 0)
        if deficit > 0:
            deficit_labels.extend([label] * deficit)
    
    # Sanity: total surplus == total deficit
    n_transfer = min(len(donor_pool), len(deficit_labels))
    if n_transfer > 0:
        arr[donor_pool[:n_transfer]] = np.array(deficit_labels[:n_transfer])
    
    return arr

Standards: type hints, NumPy docstring, O(n) peak memory usage documented.

Add a performance test in tests/test_generator.py:
  @pytest.mark.slow
  def test_rake_categorical_performance_at_scale():
      import time
      rng = np.random.default_rng(42)
      labels = ['jopara_bilingual','guarani_only','spanish_only','other']
      n = 500_000
      arr = rng.choice(labels, size=n, p=[0.46,0.34,0.15,0.05])
      targets = {'jopara_bilingual':0.46,'guarani_only':0.34,'spanish_only':0.15,'other':0.05}
      t0 = time.time()
      from population_segmentation.data.generator import _rake_categorical
      result = _rake_categorical(arr, targets, rng)
      elapsed = time.time() - t0
      assert elapsed < 1.0, f"_rake_categorical too slow at N={n}: {elapsed:.2f}s"
      for label, target in targets.items():
          observed = (result == label).mean()
          assert abs(observed - target) < 0.005
```

---

### N4.2 — `inject_flaws` duplicate rows retain original `entity_id` values
**Severity: P2**

When `inject_flaws` creates duplicates:
```python
dup_rows = df.iloc[dup_idx].copy()
```
The `dup_rows` DataFrame retains the original `entity_id` values. Real registry duplicates have the same cédula (or similar) but NOT typically the same system-generated entity_id. More importantly, the `test_raw_injector.py` test `test_dup_duplicates_present` checks `len(raw_population) > SAMPLE_SIZE` which passes, but downstream deduplication (cleaner step 5) works on cédula+name+dob similarity, not on entity_id. The entity_id uniqueness is supposed to be a property of the clean layer only. The raw layer having duplicate entity_ids is fine by design, but it's undocumented and creates confusion when the test checks `raw_population["entity_id"].nunique()`.

```
Fix and document the entity_id behavior in the raw layer for
module_a_population_segmentation/src/population_segmentation/data/raw_injector.py

1. In inject_flaws(), after creating dup_rows, assign new synthetic entity_ids
   to the duplicate rows to make them appear as distinct registry entries:
   
   dup_rows = df.iloc[dup_idx].copy()
   # Assign new entity_ids to duplicate rows: they appear as separate entries
   # in the raw registry, not as acknowledged duplicates
   max_existing_id = int(df[ENTITY_ID].max())
   dup_rows[ENTITY_ID] = np.arange(
       max_existing_id + 1,
       max_existing_id + 1 + len(dup_rows),
       dtype=np.int64
   )

2. Add a docstring note to inject_flaws():
   Add to the Returns section:
   "Note on duplicate rows: DUP flaw type appends rows with NEW entity_ids
   (as if a second registry entry was created). The duplicate is detected
   by matching on (cedula_normalized, name_normalized, dob_normalized) in
   cleaner step 5, not by entity_id. The raw layer intentionally has no
   entity_id uniqueness guarantee."

3. Update test_raw_injector.py test_dup_duplicates_present:
   Add an assertion that entity_ids in the duplicate rows are NEW (not in original):
   def test_dup_duplicates_present(self, raw_population, config):
       assert len(raw_population) > SAMPLE_SIZE
       # Duplicate rows should have entity_ids above original max
       # (they appear as new registry entries, not flagged duplicates)
       max_original_id = SAMPLE_SIZE
       high_id_count = (raw_population[ENTITY_ID] > max_original_id).sum()
       expected_dups = int(SAMPLE_SIZE * config["flaw_injection"]["duplicate_rate"])
       assert abs(high_id_count - expected_dups) <= max(3, int(expected_dups * 0.3))

4. Update population_master_raw.yaml schema contract:
   For entity_id field, change:
     unique: true
   To:
     unique: false
     description: >
       Synthetic primary key; unique in the generator output but NOT in the
       raw layer after flaw injection. DUP flaw type adds rows with new
       entity_ids. Uniqueness is enforced only in population_master_clean.
```

---

## PHASE N5: MLflow and DVC Bootstrap

---

### N5.1 — MLflow referenced everywhere but never initialized
**Severity: P2**

`.env.example` sets `MLFLOW_TRACKING_URI=./mlflow/mlruns` and `MLFLOW_EXPERIMENT_NAME_A=module_a_segmentation`. The `docker-compose.yml` starts an MLflow server. The `pyproject.toml` depends on `mlflow >= 2.12`. But zero lines of production code call `mlflow.set_experiment()`, `mlflow.start_run()`, or log any metrics. The MLflow integration is entirely decorative.

```
Initialize MLflow experiment tracking in a new file and wire it into the pipeline.

CREATE: module_a_population_segmentation/src/population_segmentation/utils/tracking.py

Content:
"""MLflow experiment tracking utilities.

Provides a thin wrapper around MLflow to log pipeline runs,
QA gate results, model metrics, and calibration anchor compliance.
All MLflow calls are optional — if MLflow is unavailable, operations
degrade gracefully with a WARNING log.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger(__name__)

EXPERIMENT_NAME_A: str = os.environ.get(
    "MLFLOW_EXPERIMENT_NAME_A", "module_a_segmentation"
)


def init_mlflow() -> bool:
    """Initialize MLflow with the configured tracking URI.

    Returns:
        True if MLflow initialized successfully, False if unavailable.
    """
    try:
        import mlflow
        tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "./mlflow/mlruns")
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(EXPERIMENT_NAME_A)
        logger.info("MLflow initialized: %s / %s", tracking_uri, EXPERIMENT_NAME_A)
        return True
    except Exception as exc:
        logger.warning("MLflow unavailable — metrics will not be tracked: %s", exc)
        return False


@contextmanager
def pipeline_run(
    run_name: str,
    tags: dict[str, str] | None = None,
) -> Generator[Any, None, None]:
    """Context manager wrapping an MLflow run.

    Degrades gracefully if MLflow is unavailable.
    Usage:
        with pipeline_run("cleaner") as run:
            if run:
                mlflow.log_param("sample_size", n)
    """
    try:
        import mlflow
        with mlflow.start_run(run_name=run_name, tags=tags or {}) as run:
            logger.info("MLflow run started: %s (%s)", run_name, run.info.run_id)
            yield run
    except Exception as exc:
        logger.warning("MLflow run failed to start: %s — continuing without tracking", exc)
        yield None


def log_qa_report(qa_report: Any) -> None:
    """Log QA gate results to the active MLflow run.

    Args:
        qa_report: QAReport dataclass instance.
    """
    try:
        import mlflow
        mlflow.log_metric("input_row_count", qa_report.input_row_count)
        mlflow.log_metric("output_row_count", qa_report.output_row_count)
        mlflow.log_metric("cedula_invalid_rate", qa_report.cedula_invalid_rate)
        mlflow.log_metric("duplicate_collapse_count", qa_report.duplicate_collapse_count)
        mlflow.log_metric("rural_flag_mean", qa_report.rural_flag_mean)
        all_passed = all(qa_report.calibration_gate_results.values())
        mlflow.log_metric("calibration_gates_passed", int(all_passed))
        for gate_name, passed in qa_report.calibration_gate_results.items():
            mlflow.log_metric(f"gate_{gate_name}", int(passed))
        logger.info("QA report logged to MLflow.")
    except Exception as exc:
        logger.warning("Failed to log QA report to MLflow: %s", exc)


Add MLFLOW_TRACKING_URI to the constant block in tracking.py:
TRACKING_URI: Final[str] = os.environ.get("MLFLOW_TRACKING_URI", "./mlflow/mlruns")

Add to CANONICAL constants in schema.py:
MLFLOW_RUN_ID: Final = "mlflow_run_id"

Add init_mlflow() call to every __main__ entry point:
  from population_segmentation.utils.tracking import init_mlflow
  init_mlflow()

Add to existing tests — test that init_mlflow() returns bool (not raises):
  def test_init_mlflow_does_not_crash():
      from population_segmentation.utils.tracking import init_mlflow
      result = init_mlflow()
      assert isinstance(result, bool)
```

---

### N5.2 — DVC is referenced but not initialized; no `.dvc/` directory exists
**Severity: P2**

`.env.example` has `DVC_REMOTE_URL=` and the quality standards mandate data versioning via DVC. Nothing is initialized.

```
Initialize DVC with local-only configuration and document the remote setup path.

Run the following sequence (requires dvc to be installed via poetry install first):

# Initialize DVC in the repo root
poetry run dvc init

# Create a local DVC cache (separate from git)
poetry run dvc config cache.type hardlink,symlink

# Track the data directories
poetry run dvc add data/raw/.gitkeep
# When data files are generated, they will be tracked as:
# poetry run dvc add data/interim/population_master_raw.parquet
# poetry run dvc add data/processed/population_master_clean.parquet

# Add a dvc.yaml pipeline definition
cat > dvc.yaml << 'EOF'
stages:
  generate:
    cmd: poetry run python -m population_segmentation.data.generator
         --config module_a_population_segmentation/config/generation.yaml
         --output data/interim/population_master_raw.parquet
    deps:
      - module_a_population_segmentation/src/population_segmentation/data/generator.py
      - module_a_population_segmentation/config/generation.yaml
    outs:
      - data/interim/population_master_raw.parquet

  clean:
    cmd: poetry run python -m population_segmentation.data.cleaner
         --input data/interim/population_master_raw.parquet
         --output data/processed/population_master_clean.parquet
         --config module_a_population_segmentation/config/generation.yaml
         --anchors module_a_population_segmentation/config/calibration_anchors.yaml
    deps:
      - module_a_population_segmentation/src/population_segmentation/data/cleaner.py
      - data/interim/population_master_raw.parquet
      - module_a_population_segmentation/config/calibration_anchors.yaml
    outs:
      - data/processed/population_master_clean.parquet
    metrics:
      - reports/qa_report_latest.json:
          cache: false
EOF

# Add DVC files to git (not the data itself)
git add .dvc/ dvc.yaml dvc.lock .dvcignore
git commit -m "feat: initialize DVC pipeline with generate and clean stages"

# Document the remote setup in .env.example (update the DVC section):
# DVC_REMOTE_URL=s3://your-bucket/dvc-cache   # For S3
# DVC_REMOTE_URL=gs://your-bucket/dvc-cache   # For GCS
# DVC_REMOTE_URL=/mnt/shared/dvc-cache        # For NFS/local shared drive
# Leave blank for local-only development (data stays on local disk only)

Add a Makefile target:
dvc-repro:
	poetry run dvc repro
	@echo "Pipeline reproduced. Artifacts in data/processed/"

dvc-status:
	poetry run dvc status
	poetry run dvc dag
```

---

## PHASE N6: Code Correctness Edge Cases

---

### N6.1 — `_generate_names` returns `list[str]` not `np.ndarray`; inconsistent with all other helper functions
**Severity: P3**

Every other helper in `raw_injector.py` and `generator.py` returns numpy arrays. `_generate_names` returns a Python list. When assigned to a DataFrame column this works but is inconsistent and will confuse anyone extending the code.

```
Fix _generate_names return type in
module_a_population_segmentation/src/population_segmentation/data/raw_injector.py

Replace:

def _generate_names(
    n: int,
    rng: np.random.Generator,
    name_type: str = "first",
) -> list[str]:
    pool = _FIRST_NAMES if name_type == "first" else _LAST_NAMES
    idx = rng.integers(0, len(pool), size=n)
    return [pool[i] for i in idx]

With:

def _generate_names(
    n: int,
    rng: np.random.Generator,
    name_type: str = "first",
) -> np.ndarray:
    """Generate n synthetic names from a fixed pool using seeded RNG.

    Args:
        n: Number of names to generate.
        rng: Seeded numpy Generator.
        name_type: Either "first" or "last".

    Returns:
        Object array of name strings, shape (n,).
    """
    pool = _FIRST_NAMES if name_type == "first" else _LAST_NAMES
    pool_arr = np.array(pool, dtype=object)
    idx = rng.integers(0, len(pool), size=n)
    return pool_arr[idx]

Also update the return type annotation in the function signature.
Run: poetry run pyright module_a_population_segmentation/src to confirm type check passes.
```

---

### N6.2 — `rng.random(mask.sum())` passes a numpy scalar where `int` is expected
**Severity: P3**

In `generator.py`, the rural flag generation loop:
```python
rural_flags[mask] = rng.random(mask.sum()) > urban_p
```
`mask.sum()` returns `numpy.intp`, not `int`. While this works in practice (numpy accepts its own scalar types in most contexts), it creates ambiguity that Pyright flags and can cause unexpected behavior with certain numpy random API versions.

```
Fix all instances of rng.random(mask.sum()) in generator.py to use explicit int cast.

In module_a_population_segmentation/src/population_segmentation/data/generator.py,
find ALL occurrences of:
  rng.random(mask.sum())
  rng.integers(..., size=int(mask.sum()))
  rng.choice(..., size=int(mask.sum()))

And ensure the size argument always uses int():
  rng.random(int(mask.sum()))

Also fix in the rural flag loop:
FROM:
  for i, dept in enumerate(dept_names):
      mask = dept_indices == i
      urban_p = dept_urban_share.get(dept, 0.617)
      rural_flags[mask] = rng.random(mask.sum()) > urban_p

TO:
  for i, dept in enumerate(dept_names):
      mask = dept_indices == i
      n_in_dept = int(mask.sum())
      if n_in_dept == 0:
          continue
      urban_p = dept_urban_share.get(dept, 0.617)
      rural_flags[mask] = rng.random(n_in_dept) > urban_p

The `if n_in_dept == 0: continue` guard prevents an edge case where
small sample sizes produce empty department bins.

Run: poetry run pyright module_a_population_segmentation/src
Confirm no type errors on the rng calls.
```

---

## PHASE N7: Security and Exposure Hardening

---

### N7.1 — `graphify-out/` directory contains local path and internal project name in tracked files
**Severity: P2**

`graphify-out/.graphify_root` contains `/Users/rbk/Desktop/PARAGUAY_ELLECTION`. `graphify-out/manifest.json` contains the same path for every file. `graphify-out/GRAPH_REPORT.md` mentions "PARAGUAY_ELLECTION" as the project directory name. These are gitignored and will not be committed — but the gitignore pattern needs verification and a pre-commit hook should catch accidental force-adds.

```
Harden the repo against accidental exposure of graphify-out contents.

1. Verify .gitignore is correctly excluding graphify-out/:
   git check-ignore -v graphify-out/GRAPH_REPORT.md
   git check-ignore -v graphify-out/manifest.json
   git check-ignore -v graphify-out/.graphify_root
   All three must show the gitignore rule. If any return empty, add:
   graphify-out/
   to .gitignore and run: git rm -r --cached graphify-out/ (if already tracked)

2. Install pre-commit to prevent accidental commits of sensitive paths:
   poetry add --group dev pre-commit
   
   Create .pre-commit-config.yaml:
   repos:
     - repo: https://github.com/pre-commit/pre-commit-hooks
       rev: v4.5.0
       hooks:
         - id: check-added-large-files
           args: ['--maxkb=500']
         - id: detect-private-key
         - id: no-commit-to-branch
           args: [--branch, main]
     - repo: local
       hooks:
         - id: block-internal-paths
           name: Block internal project paths in committed files
           entry: bash -c 'git diff --cached --name-only | xargs grep -l "PARAGUAY_ELLECTION\|/Users/rbk\|graphify-out" 2>/dev/null && echo "ERROR: Internal path found in staged files" && exit 1 || exit 0'
           language: system
           pass_filenames: false
   
   Install hooks:
   poetry run pre-commit install

3. Add a script to scrub the graphify cache before any demo:
   Create scripts/clean_local_artifacts.sh:
   #!/bin/bash
   # Remove all files that contain local paths or internal project names
   rm -rf graphify-out/
   find . -name "*.pyc" -delete
   find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
   echo "Local artifacts cleaned."

4. Verify AGENTS.md and CLAUDE.md are gitignored (they are, but confirm):
   git check-ignore -v AGENTS.md CLAUDE.md
```

---

## PHASE N8: Schema and Contract Gaps

---

### N8.1 — `schema_contracts/README.md` has no documentation for the `status` field used in contracts
**Severity: P2**

`population_master_clean.yaml` uses `status: ESTIMATED` on `nbi_stress_prior` but `schema_contracts/README.md` documents zero field specification keys. Any validator parsing the YAML needs to know which keys are valid and what `status` means for validation behavior.

```
Update schema_contracts/README.md to document all field specification keys.

Replace the current README with this expanded version:

# Schema Contracts

This directory contains YAML schema contracts for all datasets shared across modules.
Each contract is the authoritative source of truth for field names, types, validation
rules, and downstream consumers.

Validation is enforced in `evaluation/validator.py` at pipeline runtime.
A `QAGateFailure` exception is raised — never a warning — if any contract is violated.

## Module A outputs

| Contract file | Dataset | Consumed by |
|---|---|---|
| `population_master_raw.yaml` | Raw synthetic population with injected flaws | Module A cleaner |
| `population_master_clean.yaml` | Cleaned, validated population + features + scores | **Module B, Module C** |
| `segment_labels.yaml` | K-Means segment assignments | **Module B, Module C** |
| `participation_propensity.yaml` | Platt-calibrated propensity scores | **Module B, Module C** |
| `media_reachability_by_segment.yaml` | Aggregated reachability by segment | **Module B** |

## Field specification keys

Each field in a contract YAML may contain the following keys:

| Key | Type | Required | Description |
|---|---|---|---|
| `type` | string | Yes | pandas dtype: `int64`, `float32`, `string`, `bool` |
| `nullable` | bool | Yes | If False, zero nulls enforced. |
| `unique` | bool | No | If True, all values must be unique. |
| `allowed_values` | list | No | Exhaustive list of permitted values. |
| `min` | number | No | Minimum value for numeric fields. |
| `max` | number | No | Maximum value for numeric fields. |
| `max_rate` | float | No | Maximum rate (0–1) for flag fields (e.g., `cedula_invalid_rate < 0.02`). |
| `max_null_rate` | float | No | Maximum rate of null values. |
| `expected_true_rate` | float | No | Expected rate of True for boolean fields. |
| `tolerance_pp` | float | No | Tolerance in percentage points for `expected_true_rate`. |
| `status` | string | No | One of `VERIFIED`, `ESTIMATED`, `SYNTHETIC`. Default: `VERIFIED`. |
| `description` | string | No | Human-readable field description. |
| `pattern` | string | No | Regex pattern for string fields. |

## Field status values

The `status` key controls validation strictness in `validator.py`:

| Status | Meaning | Validation behavior |
|---|---|---|
| `VERIFIED` | Value comes from a verified primary source (TSJE, DGEEC). | Full validation: `QAGateFailure` on any tolerance breach. |
| `ESTIMATED` | Value derived from calibrated priors; not directly observed. | Warning-level logging on tolerance breach; pipeline continues. |
| `SYNTHETIC` | Value is a constructed proxy; no real-world anchor. | Calibration anchor checks skipped entirely. |

## Version policy

Any breaking change to field names, types, or validation rules requires:
1. A version bump in the contract file (`schema_version` field)
2. An entry in `reports/decision_log.md`
3. Verification that all downstream consumers handle the new schema
```

---

## PHASE N9: Final Portfolio Audit — Remaining Gaps

---

### N9.1 — Module A `app/` and `docker/` directories missing; dashboard reference in README is a dead link
**Severity: P1**

```
Create the Streamlit dashboard skeleton for Module A.

This is the deployed artifact that makes the portfolio real. Build the skeleton
so the URL in README doesn't 404 and the dashboard target is achievable.

CREATE: module_a_population_segmentation/app/streamlit_dashboard.py

"""Module A Streamlit dashboard — Population segmentation and propensity analysis.

Deployment: Render.com (see module_a_population_segmentation/docker/Dockerfile)
Local:      make dashboard
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Decision Analytics — Module A",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── State management ─────────────────────────────────────────────────────────
DATA_PATH = Path(os.environ.get("DATA_PATH", "data/processed"))
CLEAN_DATA = DATA_PATH / "population_master_clean.parquet"
SEGMENT_DATA = DATA_PATH / "segment_labels.parquet"


def main() -> None:
    """Main dashboard entry point."""
    st.title("Decision Analytics Reconstruction — Module A")
    st.caption("Population Modeling and Segmentation | Synthetic data calibrated to verified sources")

    if not CLEAN_DATA.exists():
        st.warning(
            "Population data not yet generated. "
            "Run: `make pipeline-dev` to generate synthetic population data.",
            icon="⚠️",
        )
        st.info("This dashboard will display segment profiles, calibration curves, "
                "and propensity distributions once the pipeline has run.")
        
        # Show what the dashboard will contain
        st.subheader("Dashboard components (pending pipeline execution)")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Population entities", "4,260,816", help="Calibrated to TSJE 2018")
        with col2:
            st.metric("Behavioral segments", "6", help="K-Means with DBSCAN pre-pass")
        with col3:
            st.metric("National participation rate", "61.25%", help="TSJE 2018 verified anchor")
        return

    # Full dashboard (rendered once data is available)
    import pandas as pd
    df = pd.read_parquet(CLEAN_DATA)
    st.success(f"Population loaded: {len(df):,} entities")
    
    # Sidebar controls
    with st.sidebar:
        st.header("Controls")
        k = st.selectbox("Segment count (k)", [4, 5, 6, 7, 8], index=2)
        show_calibration = st.checkbox("Show calibration curve", value=True)
    
    # Main content placeholder
    st.subheader("Segment profiles")
    if SEGMENT_DATA.exists():
        segments = pd.read_parquet(SEGMENT_DATA)
        st.dataframe(
            segments.groupby("segment_label").agg(
                count=("entity_id", "count"),
            ).reset_index(),
            use_container_width=True,
        )
    else:
        st.info("Segment labels not yet computed. Run segmentation pipeline.")


if __name__ == "__main__":
    main()


CREATE: module_a_population_segmentation/docker/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.3

# Copy dependency files
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction

# Copy application source
COPY module_a_population_segmentation/src/ ./module_a_population_segmentation/src/
COPY module_a_population_segmentation/app/ ./module_a_population_segmentation/app/
COPY module_a_population_segmentation/config/ ./module_a_population_segmentation/config/

# Install the package
RUN pip install --no-cache-dir -e .

# Non-root user
RUN useradd -m -u 1000 analytics
USER analytics

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "module_a_population_segmentation/app/streamlit_dashboard.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

After creating both files, test locally:
  make dashboard
  # Should start streamlit at http://localhost:8501
  # Will show the "pipeline not run yet" state — that's correct
```

---

### N9.2 — Consolidated master execution checklist for repository health
**Severity: Reference**

```
Create scripts/health_check.py — a single script that validates the full repository state.

Run this before every git push and before making the portfolio public.

CREATE: scripts/health_check.py

#!/usr/bin/env python3
"""Repository health check script.

Run before every git push:
  python scripts/health_check.py

Exit codes:
  0 — all checks passed
  1 — one or more checks failed
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
FAIL = "\033[91m✗\033[0m"
PASS = "\033[92m✓\033[0m"
WARN = "\033[93m⚠\033[0m"

failures: list[str] = []
warnings: list[str] = []


def check(label: str, condition: bool, severity: str = "FAIL") -> None:
    if condition:
        print(f"  {PASS} {label}")
    else:
        symbol = FAIL if severity == "FAIL" else WARN
        print(f"  {symbol} {label}")
        if severity == "FAIL":
            failures.append(label)
        else:
            warnings.append(label)


print("\n=== Repository Health Check ===\n")

# 1. Critical files exist
print("Critical files:")
check("README.md exists", (REPO_ROOT / "README.md").exists())
check("ARCHITECTURE.md exists", (REPO_ROOT / "ARCHITECTURE.md").exists())
check("IMPLEMENTATION_PLAN.md exists", (REPO_ROOT / "IMPLEMENTATION_PLAN.md").exists())
check("ROADMAP.md exists", (REPO_ROOT / "ROADMAP.md").exists())
check("pyproject.toml exists", (REPO_ROOT / "pyproject.toml").exists())
check("poetry.lock exists", (REPO_ROOT / "poetry.lock").exists())
check(".github/workflows/ci.yml exists", (REPO_ROOT / ".github/workflows/ci.yml").exists())

# 2. Internal files are gitignored
print("\nSensitive file gitignore check:")
for sensitive in ["AGENTS.md", "CLAUDE.md", "graphify-out/"]:
    result = subprocess.run(
        ["git", "check-ignore", "-q", sensitive],
        cwd=REPO_ROOT, capture_output=True
    )
    check(f"{sensitive} is gitignored", result.returncode == 0)

# 3. Config numerical correctness
print("\nConfig integrity:")
import yaml
gen_cfg = yaml.safe_load((REPO_ROOT / "module_a_population_segmentation/config/generation.yaml").read_text())
dept_sum = sum(gen_cfg["department_weights"].values())
check(f"department_weights sum to 1.0 (actual: {dept_sum:.4f})", abs(dept_sum - 1.0) < 0.001)
bin_sum = sum(gen_cfg["age_distribution"]["bin_weights"])
check(f"bin_weights sum to 1.0 (actual: {bin_sum:.4f})", abs(bin_sum - 1.0) < 0.001)

# 4. Code correctness
print("\nCode correctness:")
src = (REPO_ROOT / "module_a_population_segmentation/src/population_segmentation/data/raw_injector.py").read_text()
check("_ENCODING_GARBLES dict defined (not just list)", "_ENCODING_GARBLES: dict[str, str]" in src)
check("rural_inet not unused (used in computation)", "whatsapp_rural_penetration" in src or "rural_inet" not in src)

# 5. Module scaffold
print("\nModule scaffold:")
for d in ["module_b_resource_allocation", "module_c_forecasting_scenarios",
          "module_a_population_segmentation/app",
          "module_a_population_segmentation/docker"]:
    check(f"{d}/ directory exists", (REPO_ROOT / d).is_dir())

# 6. Data directories
print("\nData directories:")
for d in ["data/raw", "data/interim", "data/processed"]:
    check(f"{d}/ exists", (REPO_ROOT / d).is_dir(), severity="WARN")

# 7. Transformation log honesty
print("\nDocumentation honesty:")
transform_log = (REPO_ROOT / "reports/transformation_log.md").read_text()
check(
    "transformation_log.md does not falsely claim implementation",
    "All steps implemented" not in transform_log,
)

# 8. Summary
print(f"\n{'=' * 40}")
if failures:
    print(f"{FAIL} {len(failures)} checks FAILED:")
    for f in failures:
        print(f"   - {f}")
if warnings:
    print(f"{WARN} {len(warnings)} warnings:")
    for w in warnings:
        print(f"   - {w}")
if not failures and not warnings:
    print(f"{PASS} All checks passed. Repository is clean.")
elif not failures:
    print(f"{PASS} No critical failures. Address warnings before portfolio launch.")

sys.exit(1 if failures else 0)

After creating, run:
  python scripts/health_check.py
```

---

## Summary: Net-New Issues by Severity

| Issue | Severity | Phase |
|---|---|---|
| KMeans `n_jobs` → TypeError on instantiation | P0 | N1.1 |
| CI `--no-root` → all test imports fail | P0 | N1.2 |
| `rural_inet` unused; whatsapp_pen uses magic `0.42` | P1 | N1.3 |
| `max_noise_rate` value vs comment contradiction | P1 | N1.4 |
| Makefile bypasses Poetry virtualenv on all targets | P1 | N2.1 |
| `data/`, `module_b/`, `module_c/` directories absent | P1 | N2.2 |
| `transformation_log.md` falsely claims implementation | P1 | N3.1 |
| `IMPLEMENTATION_PLAN.md` linked but absent | P1 | N3.2 |
| `app/streamlit_dashboard.py` absent; README URL is dead | P1 | N9.1 |
| `_rake_categorical` memory-intensive at 4.26M scale | P2 | N4.1 |
| Duplicate rows retain original entity_ids | P2 | N4.2 |
| MLflow configured but never called anywhere in code | P2 | N5.1 |
| DVC referenced but not initialized | P2 | N5.2 |
| `graphify-out/` path exposure risk; no pre-commit guard | P2 | N7.1 |
| `schema_contracts/README.md` missing field key docs | P2 | N8.1 |
| `_generate_names` returns list instead of ndarray | P3 | N6.1 |
| `rng.random(mask.sum())` numpy scalar type unsafe | P3 | N6.2 |
| No repository health check script | Reference | N9.2 |