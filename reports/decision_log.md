# Decision Log

Records every non-trivial architectural choice: decision, alternatives considered, reason, date.

---

## 2026-05-07 — Module A: K selection strategy

**Decision:** Use k=6 as default with silhouette validation across k ∈ {4,5,6,7,8}.

**Alternatives considered:**
- DBSCAN-only segmentation: rejected because downstream allocation (Module B) requires a fixed, stable number of segments with interpretable profiles.
- k=8: silhouette diagnostic showed diminishing returns beyond k=6 and domain knowledge maps cleanly to 6 archetypes.

**Reason:** Fixed-k K-Means with domain-validated k=6 provides operationally targetable, named segments. Divergence between silhouette-optimized k and domain k=6 is logged as a quality artifact, not a blocker.

**Source:** scope_module_A §7.2

---

## 2026-05-07 — Module A: DBSCAN vs Isolation Forest for noise pre-pass

**Decision:** Use DBSCAN noise pre-pass rather than Isolation Forest.

**Alternatives considered:**
- Isolation Forest: more robust in high dimensions but produces a score (not a binary flag), requires threshold selection, and does not provide density-based intuition.
- Local Outlier Factor: similar density basis but slower at N=4.26M scale.

**Reason:** DBSCAN's noise label is deterministic given (ε, MinPts); fits the scope requirement for deterministic, seeded pipelines; well-understood behavior in the standardized feature space. MinPts = 2*p rule-of-thumb documented in scope §7.1.

**Source:** scope_module_A §7.1

---

## 2026-05-07 — Module A: Platt calibration vs isotonic regression

**Decision:** Use Platt (sigmoid) calibration rather than isotonic regression.

**Alternatives considered:**
- Isotonic regression: more flexible, but requires more calibration data and can overfit on small calibration sets. Calibration set at sample_size=100k is 20k rows — acceptable for Platt, potentially marginal for isotonic.
- Temperature scaling: simpler (1 parameter) but does not shift mean, only rescales variance.

**Reason:** Platt calibration with a 20% holdout gives stable A,B estimates at all realistic sample sizes. The two-parameter sigmoid is sufficient to correct the systematic offset typical in logistic regression scores. Documented limitation: at sample_size < 500k, calibration may be noisier — flagged in model card.

**Source:** scope_module_A §7.3

---

## 2026-05-07 — Module A: Department rake approach

**Decision:** Post-hoc department-level rake multiplier stored in calibration_anchors.yaml, applied after Platt calibration.

**Alternatives considered:**
- Department one-hot encoding: 18 dummy variables in logistic model; risks overfitting and hides the calibration target.
- Pre-computed `department_logit_offset` feature (scope approach): used as a single feature rather than one-hot; rake multiplier applied post-Platt as a final correction.

**Reason:** Separating the logistic model's discriminative power from the department-level participation rate constraint prevents calibration leak into model selection. The rake multiplier magnitude is logged and visible as a quality artifact.

**Source:** scope_module_A §7.3

---

## 2026-05-07 — Schema contracts: Module A → B → C dependency

**Decision:** Schema contracts for population_master_clean, segment_labels, participation_propensity, and media_reachability_by_segment are defined once in schema_contracts/ and validated at Module A pipeline exit.

**Reason:** These four files are the cross-module contract boundary. Defining them once, with version numbers, prevents silent breakage when Module A modeling parameters change. Breaking changes require schema_version bump + decision_log entry + integration-impact-auditor sign-off.

**Source:** scope_master §6, cross-module impact gate rule

---

## 2026-05-11 — Local Docker: Colima instead of Docker Desktop (Mac Pro maintainer)

**Decision:** Document and verify Module A `docker compose` using **Colima** + Homebrew Docker CLI; Docker Desktop is not the supported local path on Metal-degraded legacy Macs.

**Alternatives considered:** Docker Desktop GUI (rejected: freezes and GPU stack issues); dropping Docker from the repo (rejected without product sign-off).

**Reason:** Colima provides a headless Linux VM and matches project rule [`.cursor/rules/06-developer-machine-macpro-6-1.mdc`](.cursor/rules/06-developer-machine-macpro-6-1.mdc). `poetry install` in the image requires `README.md` in the build context when `readme` is set in `pyproject.toml`, so the Dockerfile copies it into `/app/`.

**Source:** task-verify Docker rows; infra hardening session
