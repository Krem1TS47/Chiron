"""Computer vision pipeline for shot charts."""

from chiron.cv.features import extract_cv_features_from_shots
from chiron.cv.heatmap import (
    generate_density_heatmap_array,
    generate_heatmap_image,
    shots_to_dataframe,
)

__all__ = [
    "extract_cv_features_from_shots",
    "generate_density_heatmap_array",
    "generate_heatmap_image",
    "shots_to_dataframe",
]
