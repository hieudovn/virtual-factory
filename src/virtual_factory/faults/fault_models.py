"""Fault data models and configuration types.

Defines the schema for faults that evolve over time with growth rates,
severity curves, symptom propagation, and recovery profiles.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FaultSeverity(str, Enum):
    """Severity levels for fault progression."""
    NONE = "none"
    INCIPIENT = "incipient"       # Early stage, barely detectable
    DEVELOPING = "developing"     # Growing, symptoms emerging
    DEGRADED = "degraded"         # Clear symptoms, nearing threshold
    CRITICAL = "critical"         # At or near failure threshold
    FAILED = "failed"             # Equipment failed
    RECOVERING = "recovering"     # Under maintenance, improving


# Severity curve shapes
SEVERITY_CURVES = {
    "linear":       lambda t: t,                    # Constant growth
    "exponential":  lambda t: 1.0 - 2 ** (-3 * t),  # Slow start, rapid end
    "logarithmic":  lambda t: 0.3 * (t ** 0.3),     # Fast start, slow growth
    "sigmoid":      lambda t: 1.0 / (1.0 + 2 ** (-10 * (t - 0.5))),  # S-curve
    "step":         lambda t: 0.0 if t < 0.8 else 1.0,  # Sudden failure
}


@dataclass(slots=True)
class FaultSymptom:
    """A measurable symptom that manifests when a fault is active.

    Attributes
    ----------
    variable : str
        Truth variable path affected (e.g. ``COMP01.bearing_temp_c``).
    effect_type : str
        One of ``additive``, ``multiplicative``, ``replacement``.
    magnitude : float
        Peak magnitude of the symptom at severity=1.0.
    noise_std : float
        Additional noise on the symptom measurement.
    delay_s : float
        Time lag before symptom appears after fault starts.
    """
    variable: str
    effect_type: str = "additive"
    magnitude: float = 1.0
    noise_std: float = 0.0
    delay_s: float = 0.0


@dataclass(slots=True)
class RecoveryProfile:
    """Defines how a fault recovers after maintenance.

    Attributes
    ----------
    method : str
        ``instant`` (immediate fix), ``linear`` (ramp down), ``exponential`` (decay).
    duration_s : float
        Time for full recovery (ignored for instant).
    residual_severity : float
        Remaining severity after recovery (0.0 = full fix, 0.1 = partial).
    """
    method: str = "instant"
    duration_s: float = 0.0
    residual_severity: float = 0.0


@dataclass(slots=True)
class MaintenanceAction:
    """A maintenance action that can be applied to a fault.

    Attributes
    ----------
    action_id : str
        Unique identifier for this maintenance action.
    action_type : str
        ``inspection``, ``repair``, ``replace``, ``overhaul``, ``lubricate``.
    duration_s : float
        How long the maintenance takes.
    recovery : RecoveryProfile
        How the fault recovers after this action.
    description : str
        Human-readable description.
    """
    action_id: str
    action_type: str = "repair"
    duration_s: float = 3600.0
    recovery: RecoveryProfile = field(default_factory=RecoveryProfile)
    description: str = ""


@dataclass(slots=True)
class FaultConfig:
    """Configuration for a fault type in the fault library.

    Attributes
    ----------
    fault_id : str
        Unique fault identifier (e.g. ``bearing_wear``).
    category : str
        Equipment category this fault applies to (e.g. ``compressor``, ``pump``).
    display_name : str
        Human-readable name.
    severity_curve : str
        One of ``linear``, ``exponential``, ``logarithmic``, ``sigmoid``, ``step``.
    growth_rate : float
        Rate of severity increase per second of active time (0.0–1.0).
    symptoms : list[FaultSymptom]
        Symptoms that manifest as severity increases.
    alarm_delay_s : float
        Time before an alarm is expected to trigger after fault onset.
    maintenance_actions : list[MaintenanceAction]
        Available maintenance actions and their recovery profiles.
    description : str
        Detailed description of the fault mechanism.
    tags : list[str]
        Searchable tags for analytics categorization.
    """
    fault_id: str
    category: str
    display_name: str
    severity_curve: str = "linear"
    growth_rate: float = 0.001
    symptoms: list[FaultSymptom] = field(default_factory=list)
    alarm_delay_s: float = 0.0
    maintenance_actions: list[MaintenanceAction] = field(default_factory=list)
    description: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class FaultInstance:
    """A running instance of a fault on a specific equipment asset.

    Attributes
    ----------
    fault_config : FaultConfig
        The fault type definition.
    equipment_id : str
        Equipment this fault is active on.
    start_time_s : float
        Simulation time when fault was injected.
    initial_severity : float
        Starting severity (0.0–1.0).
    active : bool
        Whether the fault is currently active.
    """
    fault_config: FaultConfig
    equipment_id: str
    start_time_s: float
    initial_severity: float = 0.0
    active: bool = True

    # Runtime state
    _current_severity: float = field(default=0.0, init=False)
    _elapsed_active_s: float = field(default=0.0, init=False)
    _recovery_elapsed_s: float = field(default=0.0, init=False)
    _recovery_active: bool = field(default=False, init=False)
    _pre_recovery_severity: float = field(default=0.0, init=False)
    _detected: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self._current_severity = self.initial_severity
        self._elapsed_active_s = 0.0
        self._recovery_elapsed_s = 0.0
        self._recovery_active = False
        self._pre_recovery_severity = 0.0
        self._detected = False

    @property
    def severity(self) -> float:
        """Current severity level (0.0–1.0)."""
        return self._current_severity

    @property
    def severity_label(self) -> FaultSeverity:
        """Current severity as a label."""
        s = self._current_severity
        if s <= 0.01:
            return FaultSeverity.NONE
        if s < 0.15:
            return FaultSeverity.INCIPIENT
        if s < 0.40:
            return FaultSeverity.DEVELOPING
        if s < 0.75:
            return FaultSeverity.DEGRADED
        if s < 0.95:
            return FaultSeverity.CRITICAL
        return FaultSeverity.FAILED

    @property
    def fault_id(self) -> str:
        return self.fault_config.fault_id

    @property
    def detected(self) -> bool:
        return self._detected

    def mark_detected(self) -> None:
        self._detected = True

    def advance(self, dt_s: float) -> None:
        """Advance fault progression by dt_s seconds."""
        if not self.active:
            return

        if self._recovery_active:
            self._advance_recovery(dt_s)
        else:
            self._advance_progression(dt_s)

    def _advance_progression(self, dt_s: float) -> None:
        """Grow the fault severity."""
        self._elapsed_active_s += dt_s
        # Normalized time for severity curve (0..1)
        curve_fn = SEVERITY_CURVES.get(
            self.fault_config.severity_curve, SEVERITY_CURVES["linear"]
        )
        t_norm = min(self._elapsed_active_s * self.fault_config.growth_rate, 1.0)
        curve_val = curve_fn(t_norm)
        self._current_severity = min(self.initial_severity + curve_val, 1.0)

    def _advance_recovery(self, dt_s: float) -> None:
        """Recover from fault after maintenance."""
        self._recovery_elapsed_s += dt_s
        recovery = self.fault_config.maintenance_actions[0].recovery if self.fault_config.maintenance_actions else RecoveryProfile()

        if recovery.method == "instant":
            self._current_severity = recovery.residual_severity
            self._recovery_active = False
            self.active = False
            return

        if recovery.duration_s <= 0:
            self._current_severity = recovery.residual_severity
            self._recovery_active = False
            self.active = False
            return

        progress = min(self._recovery_elapsed_s / recovery.duration_s, 1.0)

        if recovery.method == "linear":
            self._current_severity = self._pre_recovery_severity * (1.0 - progress) + recovery.residual_severity * progress
        elif recovery.method == "exponential":
            decay = 2 ** (-5 * progress)
            self._current_severity = self._pre_recovery_severity * decay + recovery.residual_severity * (1.0 - decay)

        if progress >= 1.0:
            self._current_severity = recovery.residual_severity
            self._recovery_active = False
            self.active = False

    def start_recovery(self, action: MaintenanceAction) -> None:
        """Begin recovery using the given maintenance action."""
        self._recovery_elapsed_s = 0.0
        self._pre_recovery_severity = self._current_severity
        self._recovery_active = True

    def get_symptom_value(self, symptom: FaultSymptom, current_time_s: float) -> float:
        """Compute the current value of a symptom given the fault state."""
        if not self.active:
            return 0.0

        elapsed_since_start = current_time_s - self.start_time_s
        if elapsed_since_start < symptom.delay_s:
            return 0.0

        base = self._current_severity * symptom.magnitude
        if symptom.noise_std > 0:
            import random
            base += random.gauss(0, symptom.noise_std)
        return base


class FaultLibrary:
    """Registry of available fault configurations, organized by equipment category."""

    def __init__(self, faults: list[FaultConfig] | None = None):
        self._faults: dict[str, FaultConfig] = {}
        self._by_category: dict[str, list[str]] = {}
        if faults:
            for f in faults:
                self.register(f)

    def register(self, fault: FaultConfig) -> None:
        self._faults[fault.fault_id] = fault
        self._by_category.setdefault(fault.category, []).append(fault.fault_id)

    def get(self, fault_id: str) -> FaultConfig | None:
        return self._faults.get(fault_id)

    def list_by_category(self, category: str) -> list[FaultConfig]:
        ids = self._by_category.get(category, [])
        return [self._faults[fid] for fid in ids if fid in self._faults]

    def list_all(self) -> list[FaultConfig]:
        return list(self._faults.values())

    def categories(self) -> list[str]:
        return list(self._by_category.keys())

    def __len__(self) -> int:
        return len(self._faults)

    def __contains__(self, fault_id: str) -> bool:
        return fault_id in self._faults
