# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Re-export: implementation lives in ``pipeline.models.segmentation``."""

from population_segmentation.pipeline.models.segmentation import (
    FEATURE_COLUMNS,
    LABEL_SCORE_WEIGHTS,
    PROFILE_FEATURES,
    SEGMENT_LABEL_MAP,
    DBSCANNoiseFilter,
    KMeansSegmenter,
    _matrix,  # pyright: ignore[reportPrivateUsage]
    assign_segment_labels,
    build_segmentation_frame,
    cluster_profiles,
)

__all__ = [
    "DBSCANNoiseFilter",
    "FEATURE_COLUMNS",
    "KMeansSegmenter",
    "LABEL_SCORE_WEIGHTS",
    "PROFILE_FEATURES",
    "SEGMENT_LABEL_MAP",
    "_matrix",
    "assign_segment_labels",
    "build_segmentation_frame",
    "cluster_profiles",
]
