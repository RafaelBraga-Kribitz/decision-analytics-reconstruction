# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Participation propensity model with calibration gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "age_bin_encoded",
    "gender_encoded",
    "rural_flag",
    "youth_flag",
    "senior_flag",
    "metro_flag",
    "structural_dependency_encoded",
    "preference_proxy_strength",
    "internet_access_flag",
]


@dataclass
class PropensityModel:
    """Logistic propensity with Platt scaling and calibration-aware synthetic labels.

    Attributes:
        random_state: Integer seed passed to :mod:`sklearn` splitters and models and
            to :class:`numpy.random.Generator` for the synthetic binary target. Two
            fits with the same ``random_state``, ``df``, and ``anchors`` return
            identical prediction vectors and metric scalars (within floating-point
            equality of sklearn outputs).
        stratify_by: Tuple of column names used to build stratified train or test
            partitions when class balance allows.
    """

    random_state: int = 42
    individual_spread_std: float = 0.065
    stratify_by: tuple[str, ...] = field(
        default_factory=lambda: ("department", "age_bin_encoded", "gender_encoded")
    )

    def fit_predict(self, df: pd.DataFrame, anchors: dict[str, object]) -> dict[str, object]:
        """Fit a Platt-calibrated logistic propensity model and score the frame.

        Builds a synthetic binary target aligned to YAML anchors, trains a
        baseline logistic regression with scaling, applies Platt calibration,
        and returns metrics plus column-wise predictions on ``df``.

        Args:
            df: Feature-rich population dataset after Module A feature engineering.
            anchors: Parsed calibration anchors controlling synthetic label mass.
                Stochastic steps use the instance :attr:`random_state`; the same
                ``df`` and ``anchors`` reproduce identical returned tensors across runs.

        Returns:
            Dict with fitted artifacts, evaluation metrics, and ``prob`` column
            aligned to ``df`` index.

        Raises:
            ValueError: If stratification columns are missing or unusable.

        Example:
            Access via ``PropensityModel().fit_predict`` from the export pipeline
            once stratification columns exist on ``df``.
        """
        a = cast(dict[str, Any], anchors)  # heterogeneous nested calibration YAML
        x = self._feature_matrix(df, a)

        # Synthetic target calibrated to anchors (for reconstruction setting)
        y = self._synthetic_target(df, a)

        strat_cols = self.stratify_by
        if not strat_cols:
            raise ValueError("stratify_by must name at least one column")
        missing = [c for c in strat_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Stratification columns missing from DataFrame: {missing}")
        if len(strat_cols) > 1:
            strat_series = df[list(strat_cols)].astype(str).agg("_".join, axis=1)
        elif len(strat_cols) == 1:
            strat_series = df[strat_cols[0]]
        else:
            raise ValueError("stratify_by must name at least one column")
        try:
            x_train, x_tmp, y_train, y_tmp = train_test_split(
                x, y, test_size=0.4, random_state=self.random_state, stratify=strat_series
            )
        except ValueError:
            # Rare strata (small n or high-cardinality composite keys) — fall back to department.
            x_train, x_tmp, y_train, y_tmp = train_test_split(
                x, y, test_size=0.4, random_state=self.random_state, stratify=df["department"]
            )
        x_cal, x_test, y_cal, y_test = train_test_split(
            x_tmp, y_tmp, test_size=0.5, random_state=self.random_state
        )

        scaler = StandardScaler()
        x_train_s = scaler.fit_transform(x_train)
        x_cal_s = scaler.transform(x_cal)
        x_test_s = scaler.transform(x_test)
        x_all_s = scaler.transform(x)

        base = LogisticRegression(max_iter=1000, random_state=self.random_state)
        base.fit(x_train_s, y_train)
        raw_cal = base.decision_function(x_cal_s)
        raw_test = base.decision_function(x_test_s)
        raw_all = base.decision_function(x_all_s)

        # Platt scaling: logistic on raw scores against calibration set
        platt = LogisticRegression(max_iter=1000, random_state=self.random_state)
        platt.fit(raw_cal.reshape(-1, 1), y_cal)
        prob_test = platt.predict_proba(raw_test.reshape(-1, 1))[:, 1]
        prob_all = platt.predict_proba(raw_all.reshape(-1, 1))[:, 1]

        # Per-department rake, then restore individual spread from raw logits.
        prob_raked, dept_multipliers = self._rake(prob_all, pd.Series(df["department"]), a)
        entity_signal = self._entity_spread_signal(df)
        prob_final = self._spread_within_departments(
            prob_raked, entity_signal, pd.Series(df["department"])
        )

        # Build metrics on test partition
        auc = float(roc_auc_score(y_test, prob_test))
        brier = float(brier_score_loss(y_test, prob_test))

        # Honest discrimination metric (IMP-A01 / F-079): auc_roc is CIRCULAR —
        # the synthetic target and department_logit_offset both derive from
        # calibration_anchors.department_participation_rates, so auc_roc mostly
        # measures that shared lookup table. auc_roc_ablated refits the same
        # split WITHOUT department_logit_offset (the leaked feature) and is the
        # number gated in CI and quoted in the README. One extra LR fit on the
        # train partition — well within the export runtime budget.
        auc_ablated, keep = self._ablated_auc(x_train, x_test, y_train, y_test, x.shape[1])

        pred = pd.Series(prob_final, index=df.index, name="participation_propensity")
        calibration = self._calibration_report(pred, df, a)

        feature_names = list(FEATURES) + ["department_logit_offset", "gender_youth_interaction"]
        ablated_feature_names = [n for i, n in enumerate(feature_names) if i in keep]

        return {
            "predictions": pred,
            "raw_logit_score": pd.Series(raw_all, index=df.index),
            "department_rake_multiplier": dept_multipliers,
            "metrics": {
                # auc_roc is circular (label and strongest feature share one
                # anchor table) — kept for continuity, never gated. The gated,
                # README-quoted discrimination figure is auc_roc_ablated.
                "auc_roc": auc,
                "auc_roc_ablated": auc_ablated,
                "brier_score": brier,
            },
            "calibration": calibration,
            "fitted_model": base,
            "scaler": scaler,
            "feature_names": feature_names,
            "ablated_feature_names": ablated_feature_names,
            "x_all_scaled": x_all_s,
        }

    def _ablated_auc(
        self,
        x_train: Any,  # Any: train_test_split's overloads return loosely-typed arrays
        x_test: Any,
        y_train: Any,
        y_test: Any,
        n_features: int,
    ) -> tuple[float, list[int]]:
        """Refit on the same split without ``department_logit_offset`` and score.

        The honest Gate A8 metric (IMP-A01 / F-079): the leaked anchor-derived
        feature is structurally excluded before fitting, so the returned AUC
        cannot read the label's source table through that column. The kept
        column indices are returned so callers can expose the ablated feature
        list for leakage checks.

        Args:
            x_train: Training design matrix (full feature set).
            x_test: Test design matrix (full feature set).
            y_train: Training labels.
            y_test: Test labels.
            n_features: Total column count of the full design matrix.

        Returns:
            ``(auc_roc_ablated, kept_column_indices)``.

        Raises:
            ValueError: Propagated from sklearn on degenerate inputs.

        Example:
            Called once per :meth:`fit_predict`; deterministic under
            ``random_state``.
        """
        offset_idx = len(FEATURES)  # department_logit_offset column position
        keep = [i for i in range(n_features) if i != offset_idx]
        scaler_abl = StandardScaler()
        x_train_abl = scaler_abl.fit_transform(np.asarray(x_train)[:, keep])
        x_test_abl = scaler_abl.transform(np.asarray(x_test)[:, keep])
        base_abl = LogisticRegression(max_iter=1000, random_state=self.random_state)
        base_abl.fit(x_train_abl, y_train)
        prob_test_abl = base_abl.predict_proba(x_test_abl)[:, 1]
        return float(roc_auc_score(y_test, prob_test_abl)), keep

    def _feature_matrix(self, df: pd.DataFrame, anchors: dict[str, Any]) -> np.ndarray:
        x = df[FEATURES].copy()
        dept_rates = anchors["department_participation_rates"]
        national = float(anchors["national"]["participation_rate"])
        # Department participation rate as logit prior (in model_params.yaml but
        # previously absent from the feature matrix — added here as a strong
        # department-level signal for the propensity classifier).
        x = x.assign(
            department_logit_offset=df["department"].map(
                lambda d: float(
                    np.log(
                        max(1e-6, float(dept_rates.get(d, national)))
                        / max(1e-6, 1.0 - float(dept_rates.get(d, national)))
                    )
                )
            ),
            gender_youth_interaction=x["gender_encoded"] * x["youth_flag"].astype(float),
        )
        return x.astype(float).to_numpy()

    def _synthetic_target(self, df: pd.DataFrame, anchors: dict[str, Any]) -> np.ndarray:
        """Generate synthetic participation labels consistent with calibration anchors.

        Uses national rate as a base so the expected target mean equals 0.6125
        regardless of department distribution.  Department-level deviations encode
        known participation differentials (Pdte Hayes −0.29, etc.).  Youth and
        gender adjustments are zero-sum (equal expected contribution across the
        population) so they do not bias the national mean.
        """
        rng = np.random.default_rng(self.random_state)
        national = float(anchors["national"]["participation_rate"])
        dept_rates = anchors["department_participation_rates"]

        # Department deviation from national (encodes the strong dept-level signal)
        dept_deviation = (
            df["department"]
            .map(lambda d: float(dept_rates.get(d, national)) - national)
            .values.astype(float)
        )

        # Youth: zero-sum adjustment (youth_rate - national for youth, balanced for non-youth)
        youth_frac = float(df["youth_flag"].mean())
        youth_adj = float(anchors["national"]["youth_participation_rate"]) - national
        non_youth_adj = -youth_adj * youth_frac / max(1e-6, 1.0 - youth_frac)

        # Gender: symmetric small signal (consistent with model card notes on approx calibration)
        gender_adj = np.where(df["gender"] == "F", 0.02, -0.02)

        base = national + dept_deviation
        base += np.where(df["youth_flag"], youth_adj, non_youth_adj)
        base += gender_adj
        base = np.clip(base, 0.05, 0.95)
        return (rng.random(len(df)) < base).astype(int)

    def _rake(
        self, p: np.ndarray, dept: pd.Series, anchors: dict[str, Any]
    ) -> tuple[np.ndarray, pd.Series]:
        """Per-department multiplicative rake to TSJE-verified participation rates.

        The calibration_anchors YAML only has complete department targets for 4
        verified departments; the remaining 14 are set to the national placeholder
        0.6125.  Because the most populous departments (Central, Alto Parana) have
        below-national verified rates, the population-weighted average of all
        department targets is below 0.6125 in the synthetic data — so a national
        rake is not applied here (it would conflict with the verified dept targets).
        The _calibration_report records the true post-rake national mean so this
        known data gap is observable in reports.
        """
        out = p.copy()
        national = float(anchors["national"]["participation_rate"])
        dept_targets = anchors["department_participation_rates"]

        multipliers: dict[str, float] = {}
        for d in dept.unique():
            mask = dept == d
            current = float(out[mask].mean())
            target = float(dept_targets.get(str(d), national))
            mult = 1.0 if current == 0 else target / current
            multipliers[str(d)] = mult
            out[mask] = np.clip(out[mask] * mult, 0.0, 1.0)
            # Iterative additive correction: when clipping at 1.0 prevents the
            # multiplicative factor from reaching the target, redistribute the
            # residual across entities that have not hit the boundary.
            mask_idx = np.where(mask)[0]  # integer indices into full array
            for _ in range(5):
                current_after = float(out[mask_idx].mean())
                residual = target - current_after
                if abs(residual) < 1e-5:
                    break
                free_flags = out[mask_idx] < 0.9999
                if not free_flags.any():
                    break
                free_idx = mask_idx[free_flags]
                delta = residual * float(len(mask_idx)) / float(len(free_idx))
                out[free_idx] = np.clip(out[free_idx] + delta, 0.0, 1.0)

        return out, pd.Series(dept.map(multipliers).to_numpy(), index=dept.index)

    def _entity_spread_signal(self, df: pd.DataFrame) -> np.ndarray:
        """Composite z-score driving the COSMETIC dispersion restoration step.

        This is not modeled uncertainty and not "individual variation" in any
        inferential sense (IMP-A01 / F-079): it z-scores eight unrelated
        demographic/behavioral columns and sums them, purely so the post-rake
        distribution is not visually collapsed within departments. The model
        card's Known Limitations section states this; a principled replacement
        (prediction-interval or per-entity bootstrap variance) would supersede
        this step.
        """
        spread_cols = [
            "age_bin_encoded",
            "gender_encoded",
            "rural_flag",
            "senior_flag",
            "metro_flag",
            "structural_dependency_encoded",
            "preference_proxy_strength",
            "internet_access_flag",
        ]
        mat = df[spread_cols].astype(float).to_numpy()
        col_std = np.maximum(mat.std(axis=0), 1e-9)
        mat_z = (mat - mat.mean(axis=0)) / col_std
        return mat_z.sum(axis=1)

    def _spread_within_departments(
        self,
        prob: np.ndarray,
        individual_signal: np.ndarray,
        dept: pd.Series,
    ) -> np.ndarray:
        """Affine remap within departments using zero-mean entity z-scores.

        COSMETIC dispersion restoration (IMP-A01 / F-079): Platt scaling and
        department raking collapse dispersion; this step re-spreads propensity
        around each department's raked mean to a fixed ``individual_spread_std``
        while preserving department means for calibration gates. The spread is
        an affine rescale of :meth:`_entity_spread_signal`'s composite z-score —
        not a posterior, bootstrap, or any other uncertainty-derived quantity.
        """
        out = prob.copy()
        spread_std = self.individual_spread_std
        for dept_name in dept.unique():
            mask_idx = np.where(dept == dept_name)[0]
            mu = float(out[mask_idx].mean())
            z = individual_signal[mask_idx] - individual_signal[mask_idx].mean()
            z_std = float(z.std())
            if z_std > 1e-9:
                z = z / z_std
            else:
                # Deterministic micro-jitter from entity index when signal is flat.
                z = (np.arange(len(mask_idx), dtype=float) - len(mask_idx) / 2.0) / max(
                    len(mask_idx), 1
                )
                z_std = float(z.std())
                if z_std > 1e-9:
                    z = z / z_std
            out[mask_idx] = np.clip(mu + z * spread_std, 0.0, 1.0)
            for _ in range(8):
                residual = mu - float(out[mask_idx].mean())
                if abs(residual) < 1e-5:
                    break
                free = out[mask_idx] < 0.9999
                if not free.any():
                    break
                out[mask_idx][free] = np.clip(out[mask_idx][free] + residual, 0.0, 1.0)
        return out

    def _calibration_report(
        self, pred: pd.Series, df: pd.DataFrame, anchors: dict[str, Any]
    ) -> dict[str, Any]:
        youth_mean = float(pred[df["youth_flag"]].mean())
        female_mean = float(pred[df["gender"] == "F"].mean())
        male_mean = float(pred[df["gender"] == "M"].mean())
        dept_means = {
            d: float(pred[df["department"] == d].mean())
            for d in ["Presidente Hayes", "Alto Parana", "Central", "Guaira"]
        }
        return {
            "national_mean": float(pred.mean()),
            "youth_mean": youth_mean,
            "female_mean": female_mean,
            "male_mean": male_mean,
            "dept_means": dept_means,
            "targets": {
                "national": float(anchors["national"]["participation_rate"]),
                "youth": float(anchors["national"]["youth_participation_rate"]),
            },
        }
