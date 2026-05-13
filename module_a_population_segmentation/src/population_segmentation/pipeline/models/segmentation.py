"""Segmentation models: DBSCAN noise filter + KMeans segmenter."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

# Canonical k=6 segment label map — index 0–5 (KMeans cluster index → name).
# Source of truth for all downstream consumers (dashboard, export pipeline, schema contracts).
SEGMENT_LABEL_MAP: dict[int, str] = {
    0: "rural_committed",
    1: "urban_high_volatility",
    2: "youth_volatile",
    3: "structurally_dependent_bloc",
    4: "rural_low_propensity",
    5: "committed_opposition",
}

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


def _matrix(df: pd.DataFrame, n_pca_components: int = 5) -> np.ndarray:
    """Standardize then reduce dimensionality with PCA.

    PCA before DBSCAN and KMeans is necessary because in the raw 13-dimensional
    standardized feature space the median inter-point distance is ~0.75, making
    density-based thresholds very sensitive to dimensionality.  Five principal
    components capture the dominant variance while making eps/silhouette
    thresholds stable and interpretable.
    """
    x = df[FEATURE_COLUMNS].astype(float).to_numpy()
    x_scaled = StandardScaler().fit_transform(x)
    return PCA(n_components=n_pca_components, random_state=42).fit_transform(x_scaled)


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
    k: int = 6
    random_state: int = 42

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

    def _bootstrap_ari(self, x: np.ndarray, full_labels: np.ndarray) -> float:
        rng = np.random.default_rng(self.random_state)
        n = len(x)
        scores: list[float] = []
        for _ in range(25):
            idx = rng.choice(n, size=max(100, int(0.8 * n)), replace=False)
            km = KMeans(
                n_clusters=self.k, init="k-means++", n_init="auto", random_state=self.random_state
            )
            labels_sub = km.fit_predict(x[idx])
            ari = adjusted_rand_score(full_labels[idx], labels_sub)
            scores.append(float(ari))
        return float(np.mean(scores))


def build_segmentation_frame(
    df: pd.DataFrame,
    k: int = 6,
    random_state: int = 42,
) -> tuple[pd.DataFrame, dict]:
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

    labels_df = pd.DataFrame(
        {
            "entity_id": df["entity_id"].to_numpy(),
            "segment_id": kmeans_labels,
            "segment_label": pd.Series(kmeans_labels).map(SEGMENT_LABEL_MAP).to_numpy(),
            "dbscan_noise_flag": dbscan_noise_flag,
        }
    )

    metrics_dict: dict = {
        "silhouette": seg_out["silhouette"],
        "bootstrap_ari": seg_out["bootstrap_ari"],
        "noise_rate": float(noise_result["noise_rate"]),
        "segment_share": seg_out["segment_share"],
    }

    return labels_df, metrics_dict
