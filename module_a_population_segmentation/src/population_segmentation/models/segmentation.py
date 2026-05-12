"""Re-export: implementation lives in ``pipeline.models.segmentation``."""

from population_segmentation.pipeline.models.segmentation import (
    FEATURE_COLUMNS,
    SEGMENT_LABEL_MAP,
    DBSCANNoiseFilter,
    KMeansSegmenter,
    _matrix,
    build_segmentation_frame,
)

__all__ = [
    "DBSCANNoiseFilter",
    "FEATURE_COLUMNS",
    "KMeansSegmenter",
    "SEGMENT_LABEL_MAP",
    "_matrix",
    "build_segmentation_frame",
]
