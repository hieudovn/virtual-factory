"""Enhanced Sensor & Data Quality Model.

Models realistic sensor behaviors that challenge analytics pipelines:
- Noise, Bias, Drift
- Delay, Flatline
- Missing data (intermittent loss)
- Communication loss (burst dropouts)
- Sample rate mismatch
- Calibration offset
- Quantization error
"""

from virtual_factory.sensor_quality.quality_model import (
    SensorQualityModel,
    SensorQualityProfile,
    QualityDegradation,
)

__all__ = [
    "SensorQualityModel",
    "SensorQualityProfile",
    "QualityDegradation",
]
