"""Re-export: implementation lives in ``pipeline.models.propensity``."""

from population_segmentation.pipeline.models.propensity import (
    PropensityModel,
    synthetic_training_reference_labels,
)

__all__ = ["PropensityModel", "synthetic_training_reference_labels"]
