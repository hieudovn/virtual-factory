"""Tests for the Sensor Quality Model."""

import pytest

from virtual_factory.sensor_quality.quality_model import (
    SensorQualityModel,
    SensorQualityProfile,
    QualityDegradation,
)


class TestSensorQualityModel:
    def test_no_degradation(self):
        model = SensorQualityModel()
        val, quality = model.apply(100.0, 0.0)
        assert val == 100.0
        assert quality == "GOOD"

    def test_noise_increase(self):
        model = SensorQualityModel()
        model.add_profile(SensorQualityProfile(
            QualityDegradation.NOISE_INCREASE,
            start_time_s=0.0,
            intensity=1.0,
            params={"noise_multiplier": 5.0},
        ))
        # With high noise_std input, the value should vary
        values = []
        for _ in range(100):
            val, q = model.apply(100.0, 0.0, noise_std=2.0)
            values.append(val)
        # Some variation expected
        assert len(set(round(v, 2) for v in values)) > 5

    def test_bias_shift(self):
        model = SensorQualityModel()
        model.add_profile(SensorQualityProfile(
            QualityDegradation.BIAS_SHIFT,
            start_time_s=0.0,
            intensity=1.0,
            params={"bias_value": 5.0},
        ))
        val, quality = model.apply(100.0, 0.0)
        assert val == 105.0
        assert quality == "GOOD"

    def test_flatline(self):
        model = SensorQualityModel()
        model.add_profile(SensorQualityProfile(
            QualityDegradation.FLATLINE,
            start_time_s=0.0,
            params={"flatline_value": 50.0},
        ))
        # First call sets flatline value
        val1, q1 = model.apply(100.0, 0.0)
        assert val1 == 50.0
        assert q1 == "BAD"

        # Subsequent calls return same flatline
        val2, q2 = model.apply(200.0, 1.0)
        assert val2 == 50.0
        assert q2 == "BAD"

    def test_drift(self):
        model = SensorQualityModel()
        model.add_profile(SensorQualityProfile(
            QualityDegradation.DRIFT,
            start_time_s=0.0,
            intensity=1.0,
            params={"drift_rate_per_s": 0.5},
        ))
        # First call: dt = 0 - (-1) = 1.0, so drift = 0.5
        val1, _ = model.apply(100.0, 0.0)
        assert val1 == pytest.approx(100.5, rel=0.01)

        # Second call after 10s: dt = 10, drift += 5.0, total = 5.5
        val2, _ = model.apply(100.0, 10.0)
        assert val2 == pytest.approx(105.5, rel=0.01)

    def test_calibration_offset(self):
        model = SensorQualityModel()
        model.add_profile(SensorQualityProfile(
            QualityDegradation.CALIBRATION_OFFSET,
            start_time_s=0.0,
            intensity=1.0,
            params={"offset_value": 3.0},
        ))
        val, quality = model.apply(100.0, 0.0)
        assert val == 103.0
        assert quality == "GOOD"

    def test_time_based_activation(self):
        model = SensorQualityModel()
        model.add_profile(SensorQualityProfile(
            QualityDegradation.BIAS_SHIFT,
            start_time_s=100.0,
            params={"bias_value": 10.0},
        ))
        # Before activation
        val, q = model.apply(100.0, 50.0)
        assert val == 100.0

        # After activation
        val, q = model.apply(100.0, 150.0)
        assert val == 110.0

    def test_time_based_expiry(self):
        model = SensorQualityModel()
        model.add_profile(SensorQualityProfile(
            QualityDegradation.BIAS_SHIFT,
            start_time_s=100.0,
            end_time_s=200.0,
            params={"bias_value": 10.0},
        ))
        val, _ = model.apply(100.0, 150.0)
        assert val == 110.0

        val, _ = model.apply(100.0, 250.0)
        assert val == 100.0  # Expired

    def test_clear_profiles(self):
        model = SensorQualityModel()
        model.add_profile(SensorQualityProfile(
            QualityDegradation.BIAS_SHIFT,
            start_time_s=0.0,
            params={"bias_value": 10.0},
        ))
        model.clear_profiles()
        val, q = model.apply(100.0, 0.0)
        assert val == 100.0
        assert q == "GOOD"
