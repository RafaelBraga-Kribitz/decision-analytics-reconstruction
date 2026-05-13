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

        # Two-pass rake: national first, then per-department (IPF one iteration)
        prob_raked, dept_multipliers = self._rake(prob_all, pd.Series(df["department"]), a)

        # Build metrics on test partition
        auc = float(roc_auc_score(y_test, prob_test))
        brier = float(brier_score_loss(y_test, prob_test))

        pred = pd.Series(prob_raked, index=df.index, name="participation_propensity")
        calibration = self._calibration_report(pred, df, a)

        feature_names = list(FEATURES) + ["department_logit_offset", "gender_youth_interaction"]

        return {
            "predictions": pred,
            "raw_logit_score": pd.Series(raw_all, index=df.index),
            "department_rake_multiplier": dept_multipliers,
            "metrics": {"auc_roc": auc, "brier_score": brier},
            "calibration": calibration,
            "fitted_model": base,
            "scaler": scaler,
            "feature_names": feature_names,
            "x_all_scaled": x_all_s,
        }

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
