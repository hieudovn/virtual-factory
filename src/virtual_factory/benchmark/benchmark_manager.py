"""Ground Truth & Benchmark Manager.

Generates and exports hidden labels for analytics validation:
- Operating states per equipment per timestep
- Active fault types, start times, and severities
- Asset health indices and remaining useful life (simulated)
- Failure probabilities and expected diagnoses

These labels are NEVER published as industrial telemetry — they exist
solely for analytics model validation and benchmarking.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BenchmarkMode(str, Enum):
    """Benchmark output mode."""
    INDUSTRIAL = "industrial"     # Normal telemetry only, no labels exposed
    BENCHMARK = "benchmark"       # Labels exported alongside telemetry
    HIDDEN = "hidden"             # Labels stored but not exportable (for blind tests)


@dataclass
class BenchmarkLabels:
    """Per-timestep ground truth labels for analytics validation.

    These are the "answer key" for analytics model evaluation.
    """

    timestamp_s: float
    equipment_id: str

    # Operating state
    operating_state: str = "unknown"

    # Fault ground truth
    active_faults: list[str] = field(default_factory=list)
    fault_severities: dict[str, float] = field(default_factory=dict)
    fault_start_times: dict[str, float] = field(default_factory=dict)

    # Health metrics
    health_index: float = 1.0
    remaining_useful_life_s: float = -1.0  # -1 = not applicable
    failure_probability: float = 0.0

    # Expected analytics output (for benchmarking)
    expected_anomaly: bool = False
    expected_diagnosis: str = ""
    expected_severity_label: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_s": self.timestamp_s,
            "equipment_id": self.equipment_id,
            "operating_state": self.operating_state,
            "active_faults": ",".join(self.active_faults),
            "fault_severities": str(self.fault_severities),
            "health_index": self.health_index,
            "remaining_useful_life_s": self.remaining_useful_life_s,
            "failure_probability": self.failure_probability,
            "expected_anomaly": self.expected_anomaly,
            "expected_diagnosis": self.expected_diagnosis,
            "expected_severity_label": self.expected_severity_label,
        }


@dataclass
class BenchmarkPackage:
    """Complete benchmark dataset for analytics development.

    Contains all exports needed for training and validation of
    industrial analytics models.
    """

    # Core telemetry (published signals)
    telemetry_records: list[dict[str, Any]] = field(default_factory=list)

    # Asset metadata
    asset_metadata: dict[str, Any] = field(default_factory=dict)

    # Operating states per equipment per timestep
    operating_state_records: list[dict[str, Any]] = field(default_factory=list)

    # Alarm events
    alarm_records: list[dict[str, Any]] = field(default_factory=list)

    # Maintenance events
    maintenance_records: list[dict[str, Any]] = field(default_factory=list)

    # Fault timeline (when faults were active, their severity, etc.)
    fault_timeline_records: list[dict[str, Any]] = field(default_factory=list)

    # Benchmark labels (hidden ground truth)
    benchmark_labels: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BenchmarkManager:
    """Collects and exports ground truth labels during simulation.

    Usage::

        mgr = BenchmarkManager(mode=BenchmarkMode.BENCHMARK)
        # Each simulation step:
        mgr.record_labels(timestamp_s, equipment_id, state_machine,
                          fault_engine)
        # At end:
        mgr.export("output/benchmark/")
    """

    mode: BenchmarkMode = BenchmarkMode.BENCHMARK
    labels: list[BenchmarkLabels] = field(default_factory=list)

    def record_labels(
        self,
        timestamp_s: float,
        equipment_id: str,
        operating_state: str = "unknown",
        active_faults: list[str] | None = None,
        fault_severities: dict[str, float] | None = None,
        fault_start_times: dict[str, float] | None = None,
        health_index: float = 1.0,
        remaining_useful_life_s: float = -1.0,
        failure_probability: float = 0.0,
        expected_anomaly: bool = False,
        expected_diagnosis: str = "",
        expected_severity_label: str = "none",
    ) -> BenchmarkLabels:
        """Record one timestep of ground truth labels."""
        if self.mode == BenchmarkMode.INDUSTRIAL:
            # In industrial mode, don't store labels
            return BenchmarkLabels(timestamp_s=timestamp_s, equipment_id=equipment_id)

        label = BenchmarkLabels(
            timestamp_s=timestamp_s,
            equipment_id=equipment_id,
            operating_state=operating_state,
            active_faults=active_faults or [],
            fault_severities=fault_severities or {},
            fault_start_times=fault_start_times or {},
            health_index=health_index,
            remaining_useful_life_s=remaining_useful_life_s,
            failure_probability=failure_probability,
            expected_anomaly=expected_anomaly,
            expected_diagnosis=expected_diagnosis,
            expected_severity_label=expected_severity_label,
        )
        self.labels.append(label)
        return label

    def record_from_engine(
        self,
        timestamp_s: float,
        equipment_id: str,
        state_machine,   # OperatingStateMachine
        fault_engine,    # FaultEngine
    ) -> BenchmarkLabels:
        """Convenience: record labels from engine objects."""
        faults = fault_engine.get_active_faults(equipment_id)
        active_ids = [f.fault_id for f in faults]
        severities = {f.fault_id: f.severity for f in faults}
        start_times = {f.fault_id: f.start_time_s for f in faults}
        health = fault_engine.get_health_index(equipment_id)

        # Determine expected anomaly
        expected_anomaly = any(f.severity > 0.1 for f in faults)

        # Determine expected diagnosis (most severe fault)
        if faults:
            most_severe = max(faults, key=lambda f: f.severity)
            expected_diagnosis = most_severe.fault_id
            expected_severity_label = most_severe.severity_label.value
        else:
            expected_diagnosis = "healthy"
            expected_severity_label = "none"

        # Simulated RUL: inverse of max severity
        max_sev = max((f.severity for f in faults), default=0.0)
        rul = -1.0
        if max_sev > 0.01:
            # Simple linear RUL: 1000s at severity=0.1, 0s at severity=1.0
            rul = max(0.0, 10000.0 * (1.0 - max_sev))

        return self.record_labels(
            timestamp_s=timestamp_s,
            equipment_id=equipment_id,
            operating_state=state_machine.current.value if state_machine else "unknown",
            active_faults=active_ids,
            fault_severities=severities,
            fault_start_times=start_times,
            health_index=health,
            remaining_useful_life_s=rul,
            failure_probability=max_sev,
            expected_anomaly=expected_anomaly,
            expected_diagnosis=expected_diagnosis,
            expected_severity_label=expected_severity_label,
        )

    def to_records(self) -> list[dict[str, Any]]:
        """Export all labels as dicts for DataFrame/Parquet."""
        return [label.to_dict() for label in self.labels]

    def build_package(
        self,
        telemetry_records: list[dict[str, Any]] | None = None,
        asset_metadata: dict[str, Any] | None = None,
        alarm_records: list[dict[str, Any]] | None = None,
        maintenance_records: list[dict[str, Any]] | None = None,
        fault_timeline_records: list[dict[str, Any]] | None = None,
    ) -> BenchmarkPackage:
        """Build a complete benchmark package from all data sources."""
        return BenchmarkPackage(
            telemetry_records=telemetry_records or [],
            asset_metadata=asset_metadata or {},
            operating_state_records=self.to_records(),
            alarm_records=alarm_records or [],
            maintenance_records=maintenance_records or [],
            fault_timeline_records=fault_timeline_records or [],
            benchmark_labels=self.to_records(),
        )

    def reset(self) -> None:
        """Clear all recorded labels."""
        self.labels.clear()
