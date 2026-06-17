# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Segmentation models: DBSCAN noise filter + KMeans segmenter.

Segment names are **profile-derived**: after KMeans fits, each canonical
label is matched to the cluster whose feature profile best fits the label's
semantics (Hungarian assignment over z-scored cluster profiles) — cluster
index order is never assumed to mean anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import yaml
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler


def _load_model_params() -> dict[str, Any]:
    """Load model parameters from centralized config."""
    config_path = Path(__file__).resolve().parents[3] / "config" / "model_params.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)

# Canonical k=6 segment label vocabulary. The historical index keys are kept
# only so downstream consumers can enumerate the canonical names and k —
# the actual cluster→name mapping is computed per fit by
# :func:`assign_segment_labels` from cluster profiles, NOT from this order.
SEGMENT_LABEL_MAP: dict[int, str] = {
    0: "rural_committed",
    1: "urban_high_volatility",
    2: "youth_volatile",
    3: "structurally_dependent_bloc",
    4: "rural_low_propensity",
    5: "committed_opposition",
}

# Label semantics as weights over z-scored cluster-profile features.
# preference_proxy encoding (features/behavioral.py): A=0, B=1, other=2, none=3;
# "opposition" below is the share of preference B, "no_preference" the share of none.
LABEL_SCORE_WEIGHTS: dict[str, dict[str, float]] = {
    "rural_committed": {"rural": 2.5, "strength": 1.5, "metro": -2.0, "opposition": -0.5},
    "urban_high_volatility": {"metro": 1.5, "strength": -1.0, "no_preference": 0.5, "rural": -0.5},
    "youth_volatile": {"youth": 1.5, "strength": -0.5},
    "structurally_dependent_bloc": {"dependency": 1.5, "nbi_stress": 0.5},
    "rural_low_propensity": {"rural": 2.0, "strength": -2.0, "nbi_stress": 0.5},
    "committed_opposition": {"opposition": 2.0, "strength": 0.5, "rural": 0.8, "metro": -0.5},
}

#: Interpretable profile features used for label assignment.
PROFILE_FEATURES: tuple[str, ...] = (
    "rural",
    "metro",
    "youth",
    "dependency",
    "strength",
    "opposition",
    "no_preference",
    "nbi_stress",
)


def cluster_profiles(df: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
    """Mean interpretable feature profile per cluster.

    Args:
        df: Entity-level feature frame (must carry the behavioral columns).
        labels: KMeans cluster index per row of ``df``.

    Returns:
        DataFrame indexed by cluster id with :data:`PROFILE_FEATURES` columns.

    Raises:
        KeyError: If a required behavioral column is missing.

    Example:
        ``cluster_profiles(feat_df, kmeans_labels).loc[3, "youth"]``.
    """
    prof = pd.DataFrame(
        {
            "rural": df["rural_flag"].astype(float),
            "metro": df["metro_flag"].astype(float),
            "youth": df["youth_flag"].astype(float),
            "dependency": df["structural_dependency_encoded"].astype(float),
            "strength": df["preference_proxy_strength"].astype(float),
            "opposition": (df["preference_proxy_encoded"] == 1).astype(float),
            "no_preference": (df["preference_proxy_encoded"] == 3).astype(float),
            "nbi_stress": df["nbi_stress_prior_scaled"].astype(float),
            "cluster": labels,
        }
    )
    return cast(pd.DataFrame, prof.groupby("cluster").mean())


def _cluster_rural_share(df: pd.DataFrame, labels: np.ndarray, cluster_id: int) -> float:
    mask = labels == cluster_id
    if not mask.any():
        return 0.0
    return float(df.loc[mask, "rural_flag"].astype(bool).mean())


def _swap_cluster_labels(mapping: dict[int, str], a: int, b: int) -> None:
    mapping[a], mapping[b] = mapping[b], mapping[a]


def _repair_committed_opposition(
    df: pd.DataFrame,
    labels: np.ndarray,
    out: dict[int, str],
    profiles: pd.DataFrame,
) -> None:
    reverse = {label: cluster_id for cluster_id, label in out.items()}
    co_id = reverse.get("committed_opposition")
    if co_id is None or _cluster_rural_share(df, labels, co_id) >= 0.01:
        return
    rural_clusters = [
        int(cluster_id)
        for cluster_id in profiles.index
        if float(profiles.loc[cluster_id, "rural"]) >= 0.01
    ]
    if not rural_clusters:
        return
    best = max(rural_clusters, key=lambda cid: float(profiles.loc[cid, "opposition"]))
    if best != co_id:
        _swap_cluster_labels(out, co_id, best)


def _repair_rural_committed(out: dict[int, str], profiles: pd.DataFrame) -> None:
    """Ensure rural_committed sits on a genuinely rural cluster (F-051 invariant)."""
    reverse = {label: cluster_id for cluster_id, label in out.items()}
    rc_id = reverse.get("rural_committed")
    if rc_id is None or float(profiles.loc[rc_id, "rural"]) >= 0.2:
        return
    donor_labels = ("urban_high_volatility", "youth_volatile", "structurally_dependent_bloc")
    donors = [reverse[name] for name in donor_labels if name in reverse]
    if not donors:
        return
    best = max(donors, key=lambda cid: float(profiles.loc[cid, "rural"]))
    if float(profiles.loc[best, "rural"]) > float(profiles.loc[rc_id, "rural"]):
        _swap_cluster_labels(out, rc_id, best)


def _repair_label_mapping(
    df: pd.DataFrame,
    labels: np.ndarray,
    mapping: dict[int, str],
    profiles: pd.DataFrame,
) -> dict[int, str]:
    """Swap cluster names when Hungarian tie-breaks invert opposition/rural semantics."""
    out = dict(mapping)
    _repair_committed_opposition(df, labels, out, profiles)

    reverse = {label: cluster_id for cluster_id, label in out.items()}
    sdb_id = reverse.get("structurally_dependent_bloc")
    if sdb_id is not None:
        best_dep = int(max(profiles.index, key=lambda cid: float(profiles.loc[cid, "dependency"])))
        if best_dep != sdb_id:
            _swap_cluster_labels(out, sdb_id, best_dep)

    _repair_rural_committed(out, profiles)
    return out


def assign_segment_labels(df: pd.DataFrame, labels: np.ndarray) -> dict[int, str]:
    """Profile-derived one-to-one mapping of cluster index → canonical name.

    Each cluster's profile is z-scored across clusters; each canonical label
    scores every cluster via :data:`LABEL_SCORE_WEIGHTS`; the Hungarian
    algorithm picks the assignment maximizing total semantic fit. The result
    is deterministic for a given fit.

    Args:
        df: Entity-level feature frame aligned with ``labels``.
        labels: KMeans cluster index per row.

    Returns:
        Dict mapping each cluster id to a unique canonical segment label.
        Clusters beyond the canonical vocabulary (k > 6) get ``segment_<id>``.

    Raises:
        KeyError: If a required behavioral column is missing from ``df``.

    Example:
        ``assign_segment_labels(feat_df, kmeans_labels)[0]``.
    """
    profiles = cluster_profiles(df, labels)
    std = cast(pd.Series, profiles.std(ddof=0)).replace(0.0, 1.0)
    z = (profiles - profiles.mean()) / std

    label_names = list(LABEL_SCORE_WEIGHTS)
    score = np.zeros((len(profiles), len(label_names)))
    for j, name in enumerate(label_names):
        for feat, w in LABEL_SCORE_WEIGHTS[name].items():
            score[:, j] += w * z[feat].to_numpy()

    rows, cols = linear_sum_assignment(-score)
    cluster_ids = profiles.index.to_numpy()
    mapping = {int(cluster_ids[r]): label_names[c] for r, c in zip(rows, cols, strict=False)}
    for cluster_id in profiles.index:
        mapping.setdefault(int(cluster_id), f"segment_{int(cluster_id)}")
    return _repair_label_mapping(df, labels, mapping, profiles)


FEATURE_COLUMNS = [
    "age_bin_encoded",
    "gender_encoded",
    "rural_flag",
    "preference_proxy_encoded",
    "preference_proxy_strength",
    "structural_dependency_encoded",
    "reachability_digital",
    "reachability_broadcast_tv",
    "reachability_broadcast_radio",
    "youth_flag",
    "metro_flag",
    "language_jopara_encoded",
    "nbi_stress_prior_scaled",
]


def _matrix(df: pd.DataFrame, n_pca_components: int | None = None) -> np.ndarray:
    """Standardize then reduce dimensionality with PCA.

    PCA before DBSCAN and KMeans is necessary because in the raw 13-dimensional
    standardized feature space the median inter-point distance is ~0.75, making
    density-based thresholds very sensitive to dimensionality.  Five principal
    components capture the dominant variance while making eps/silhouette
    thresholds stable and interpretable.
    """
    if n_pca_components is None:
        params = _load_model_params()
        n_pca_components = int(params.get("pca", {}).get("n_components", 5))
    pca_random_state = int(_load_model_params().get("pca", {}).get("random_state", 42))
    x = df[FEATURE_COLUMNS].astype(float).to_numpy()
    x_scaled = StandardScaler().fit_transform(x)
    return PCA(n_components=n_pca_components, random_state=pca_random_state).fit_transform(x_scaled)


@dataclass
class DBSCANNoiseFilter:
    eps: float = 2.0
    min_samples: int = 5

    def fit_transform(
        self, df: pd.DataFrame, *, x: np.ndarray | None = None
    ) -> dict[str, float | np.ndarray]:
        """Run DBSCAN noise detection on the PCA-reduced feature space.

        Args:
            df: Feature DataFrame containing ``FEATURE_COLUMNS``. Used only when
                ``x`` is not provided.
            x: Pre-computed PCA-reduced feature matrix from ``_matrix(df)``.
                Pass this to avoid redundant ``StandardScaler`` + ``PCA`` when
                the caller already holds the matrix.

        Returns:
            Dict with ``noise_rate`` (float, fraction noise) and ``noise_flags``
            (1-D boolean array, one row per entity).

        Raises:
            KeyError: If ``df`` is used and lacks required feature columns.

        Example:
            Invoked from :func:`build_segmentation_frame` with a shared PCA matrix.
        """
        if x is None:
            x = _matrix(df)
        labels = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric="euclidean").fit_predict(
            x
        )
        noise_flags: np.ndarray = labels == -1
        return {"noise_rate": float(noise_flags.mean()), "noise_flags": noise_flags}


@dataclass
class KMeansSegmenter:
    k: int = int(_load_model_params().get("kmeans", {}).get("default_k", 6))
    random_state: int = int(_load_model_params().get("kmeans", {}).get("random_state", 42))

    def fit_predict(
        self, df: pd.DataFrame, *, x: np.ndarray | None = None
    ) -> dict[str, np.ndarray | float | pd.Series]:
        """Fit KMeans on the PCA-reduced matrix and return labels with diagnostics.

        Args:
            df: Feature DataFrame containing ``FEATURE_COLUMNS``. Used only when
                ``x`` is not provided.
            x: Pre-computed PCA-reduced feature matrix from ``_matrix(df)``.
                Pass this to avoid redundant scaling/PCA when the caller already
                holds the matrix.

        Returns:
            Dict with ``labels`` (cluster index per row), ``silhouette`` (float),
            ``bootstrap_ari`` (mean ARI over subsamples), and ``segment_share``
            (normalized cluster counts).

        Raises:
            KeyError: If ``df`` is used and lacks required feature columns.

        Example:
            Called from :func:`build_segmentation_frame` after the DBSCAN noise pass.
        """
        if x is None:
            x = _matrix(df)
        km = KMeans(
            n_clusters=self.k, init="k-means++", n_init="auto", random_state=self.random_state
        )
        labels = km.fit_predict(x)

        sil = float(silhouette_score(x, labels))
        boot_ari = self._bootstrap_ari(x, labels)
        counts = pd.Series(labels).value_counts(normalize=True).sort_index()

        return {
            "labels": labels,
            "silhouette": sil,
            "bootstrap_ari": float(boot_ari),
            "segment_share": counts,
        }

    def _bootstrap_ari(self, x: np.ndarray, _full_labels: np.ndarray) -> float:
        """Mean ARI between two independent 80% subsample fits (platform-stable).

        Compares two independently-fitted subsamples on their shared rows only.
        BLAS differences then cancel because both label sets come from KMeans on
        the same machine for the same subsample (macOS/Linux ARI variance eliminated).
        """
        rng = np.random.default_rng(self.random_state)
        n = len(x)
        sub_size = max(100, int(0.8 * n))
        scores: list[float] = []
        for i in range(25):
            idx_a = np.sort(rng.choice(n, size=sub_size, replace=False))
            idx_b = np.sort(rng.choice(n, size=sub_size, replace=False))
            shared = np.intersect1d(idx_a, idx_b)
            if len(shared) < 50:
                continue
            km_a = KMeans(
                n_clusters=self.k, init="k-means++", n_init="auto", random_state=self.random_state
            )
            km_b = KMeans(
                n_clusters=self.k,
                init="k-means++",
                n_init="auto",
                random_state=self.random_state + 1 + i,
            )
            labels_a = km_a.fit_predict(x[idx_a])
            labels_b = km_b.fit_predict(x[idx_b])
            pos_a = np.searchsorted(idx_a, shared)
            pos_b = np.searchsorted(idx_b, shared)
            ari = adjusted_rand_score(labels_a[pos_a], labels_b[pos_b])
            scores.append(float(ari))
        return float(np.mean(scores)) if scores else 0.0


def build_segmentation_frame(
    df: pd.DataFrame,
    k: int = 6,
    random_state: int = 42,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run DBSCAN plus KMeans and return per-entity labels and summary metrics.

    Args:
        df: Feature DataFrame containing all ``FEATURE_COLUMNS`` and ``entity_id``.
        k: Number of KMeans clusters (default 6, matching contract k).
        random_state: Seed forwarded to KMeans, bootstrap ARI subsampling, and
            internal :class:`numpy.random.Generator` draws. Same ``df``, ``k``, and
            ``random_state`` reproduce ``labels_df`` and the scalar metrics in the
            returned dict.

    Returns:
        Tuple ``(labels_df, metrics_dict)`` where ``labels_df`` has one row per
        entity with ``entity_id``, ``segment_id``, ``segment_label``, and
        ``dbscan_noise_flag``; ``metrics_dict`` holds ``silhouette``,
        ``bootstrap_ari``, ``noise_rate``, and ``segment_share``.

    Raises:
        KeyError: If ``df`` is missing ``entity_id`` or a required feature column.

    Example:
        Primary segmentation entrypoint for the Module A export bundle.
    """
    # Compute the PCA-reduced feature matrix once and reuse it for both
    # DBSCAN (noise pre-pass) and KMeans, avoiding two independent fits of
    # StandardScaler + PCA on the same data.
    x = _matrix(df)

    noise_result = DBSCANNoiseFilter().fit_transform(df, x=x)
    dbscan_noise_flag: np.ndarray = np.asarray(noise_result["noise_flags"], dtype=bool)

    seg = KMeansSegmenter(k=k, random_state=random_state)
    seg_out = seg.fit_predict(df, x=x)
    kmeans_labels: np.ndarray = np.asarray(seg_out["labels"])

    label_map = assign_segment_labels(df, kmeans_labels)
    labels_df = pd.DataFrame(
        {
            "entity_id": df["entity_id"].to_numpy(),
            "segment_id": kmeans_labels,
            "segment_label": pd.Series(kmeans_labels).map(label_map).to_numpy(),
            "dbscan_noise_flag": dbscan_noise_flag,
        }
    )

    metrics_dict: dict[str, Any] = {
        "silhouette": seg_out["silhouette"],
        "bootstrap_ari": seg_out["bootstrap_ari"],
        "noise_rate": float(noise_result["noise_rate"]),
        "segment_share": seg_out["segment_share"],
    }

    return labels_df, metrics_dict
