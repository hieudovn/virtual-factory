"""Enhanced Sensor & Data Quality Model.

Models realistic sensor degradation behaviors to challenge data
foundation and analytics pipelines.
"""

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class QualityDegradation(str, Enum):
    """Types of sensor quality degradation."""
    NONE = "none"
    NOISE_INCREASE = "noise_increase"
    BIAS_SHIFT = "bias_shift"
    DRIFT = "drift"
    FLATLINE = "flatline"
    INTERMITTENT = "intermittent"
    COMM_LOSS = "comm_loss"
    CALIBRATION_OFFSET = "calibration_offset"
    SAMPLE_RATE_MISMATCH = "sample_rate_mismatch"


@dataclass
class SensorQualityProfile:
    """Defines a quality degradation profile for a sensor.

    Attributes
    ----------
    degradation_type : QualityDegradation
        Type of degradation.
    start_time_s : float
        When degradation begins.
    end_time_s : float | None
        When degradation ends (None = indefinite).
    intensity : float
        0.0–1.0, how strong the degradation effect is.
    params : dict
        Type-specific parameters.

    Noise Increase params:
        - ``noise_multiplier``: factor on existing noise_std (default 3.0).

    Bias Shift params:
        - ``bias_value``: additive offset in engineering units.

    Drift params:
        - ``drift_rate_per_s``: drift increment per second.

    Flatline params:
        - ``flatline_value``: value to hold at (default: last good).

    Intermittent params:
        - ``dropout_probability``: per-sample probability of missing (0.0–1.0).
        - ``dropout_duration_s``: max consecutive dropout duration.

    Comm Loss params:
        - ``loss_duration_s``: burst dropout duration.
        - ``loss_interval_s``: time between comm loss bursts.

    Calibration Offset params:
        - ``offset_value``: calibration offset in engineering units.

    Sample Rate Mismatch params:
        - ``effective_rate_hz``: actual sampling rate (differs from configured).
    """
    degradation_type: QualityDegradation
    start_time_s: float = 0.0
    end_time_s: float | None = None
    intensity: float = 1.0
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class SensorQualityModel:
    """Applies quality degradation profiles to sensor readings.

    Usage::

        model = SensorQualityModel()
        model.add_profile(SensorQualityProfile(
            QualityDegradation.DRIFT, start_time_s=100.0,
            params={"drift_rate_per_s": 0.001},
        ))
        # Each sample:
        raw = sensor.read_truth()
        degraded = model.apply(raw, current_time_s, sensor_config)
    """

    profiles: list[SensorQualityProfile] = field(default_factory=list)

    # Internal state
    _drift_accumulator: float = field(default=0.0, init=False)
    _last_good_value: float | None = field(default=None, init=False)
    _dropout_counter: float = field(default=0.0, init=False)
    _comm_loss_active: bool = field(default=False, init=False)
    _comm_loss_remaining: float = field(default=0.0, init=False)
    _comm_loss_timer: float = field(default=0.0, init=False)
    _flatline_value: float | None = field(default=None, init=False)
    _prev_time_s: float = field(default=-1.0, init=False)

    def add_profile(self, profile: SensorQualityProfile) -> None:
        """Add a quality degradation profile."""
        self.profiles.append(profile)

    def clear_profiles(self) -> None:
        """Remove all profiles."""
        self.profiles.clear()
        self._reset_state()

    def apply(
        self,
        raw_value: float,
        current_time_s: float,
        noise_std: float = 0.0,
        existing_bias: float = 0.0,
    ) -> tuple[float, str]:
        """Apply all active quality degradations to a raw sensor value.

        Returns (degraded_value, quality_flag).
        """
        value = float(raw_value)
        quality = "GOOD"
        active_profiles = self._active_profiles(current_time_s)

        if not active_profiles:
            self._last_good_value = value
            return value, quality

        for profile in active_profiles:
            value, quality = self._apply_one(profile, value, current_time_s, noise_std, existing_bias)

        # Track last good value for flatline/intermittent recovery
        if quality == "GOOD":
            self._last_good_value = value

        self._prev_time_s = current_time_s
        return value, quality

    def _active_profiles(self, current_time_s: float) -> list[SensorQualityProfile]:
        return [
            p for p in self.profiles
            if p.start_time_s <= current_time_s
            and (p.end_time_s is None or current_time_s <= p.end_time_s)
        ]

    def _apply_one(
        self,
        profile: SensorQualityProfile,
        value: float,
        current_time_s: float,
        noise_std: float,
        existing_bias: float,
    ) -> tuple[float, str]:
        dt = current_time_s - self._prev_time_s if self._prev_time_s >= 0 else 1.0

        if profile.degradation_type == QualityDegradation.NOISE_INCREASE:
            multiplier = float(profile.params.get("noise_multiplier", 3.0))
            effective_std = noise_std * (1.0 + (multiplier - 1.0) * profile.intensity)
            if effective_std > 0:
                value += random.gauss(0, effective_std)
            return value, "GOOD"

        elif profile.degradation_type == QualityDegradation.BIAS_SHIFT:
            bias = float(profile.params.get("bias_value", 0.0)) * profile.intensity
            return value + bias, "GOOD"

        elif profile.degradation_type == QualityDegradation.DRIFT:
            rate = float(profile.params.get("drift_rate_per_s", 0.0)) * profile.intensity
            self._drift_accumulator += rate * dt
            return value + self._drift_accumulator, "GOOD"

        elif profile.degradation_type == QualityDegradation.FLATLINE:
            if self._flatline_value is None:
                self._flatline_value = profile.params.get("flatline_value", self._last_good_value or value)
            return self._flatline_value, "BAD"

        elif profile.degradation_type == QualityDegradation.INTERMITTENT:
            prob = float(profile.params.get("dropout_probability", 0.3)) * profile.intensity
            if random.random() < prob:
                return self._last_good_value or value, "BAD"
            return value, "GOOD"

        elif profile.degradation_type == QualityDegradation.COMM_LOSS:
            loss_dur = float(profile.params.get("loss_duration_s", 5.0))
            loss_int = float(profile.params.get("loss_interval_s", 60.0))

            if self._comm_loss_active:
                self._comm_loss_remaining -= dt
                if self._comm_loss_remaining <= 0:
                    self._comm_loss_active = False
                return self._last_good_value or value, "BAD"
            else:
                self._comm_loss_timer += dt
                if self._comm_loss_timer >= loss_int:
                    self._comm_loss_active = True
                    self._comm_loss_remaining = loss_dur
                    self._comm_loss_timer = 0.0
                    return self._last_good_value or value, "BAD"
                return value, "GOOD"

        elif profile.degradation_type == QualityDegradation.CALIBRATION_OFFSET:
            offset = float(profile.params.get("offset_value", 0.0)) * profile.intensity
            return value + offset, "GOOD"

        elif profile.degradation_type == QualityDegradation.SAMPLE_RATE_MISMATCH:
            # Simplification: occasionally skip update, return last value
            effective_rate = float(profile.params.get("effective_rate_hz", 0.5))
            configured_rate = 1.0  # assumed 1 Hz
            skip_prob = max(0, 1.0 - effective_rate / configured_rate)
            if random.random() < skip_prob * profile.intensity:
                return self._last_good_value or value, "GOOD"
            return value, "GOOD"

        return value, quality

    def _reset_state(self) -> None:
        self._drift_accumulator = 0.0
        self._last_good_value = None
        self._dropout_counter = 0.0
        self._comm_loss_active = False
        self._comm_loss_remaining = 0.0
        self._comm_loss_timer = 0.0
        self._flatline_value = None
        self._prev_time_s = -1.0
