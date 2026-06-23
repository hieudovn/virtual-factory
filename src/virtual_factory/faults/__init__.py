"""Fault Lifecycle Engine.

Models faults that evolve over time with configurable growth rates,
severity curves, symptom propagation, alarm delays, maintenance actions,
and recovery profiles.

The engine is driven by configuration, not hard-coded per equipment type.
"""

from virtual_factory.faults.fault_engine import FaultEngine, FaultScheduler
from virtual_factory.faults.fault_loader import (
    load_fault_library,
    load_fault_libraries,
    build_default_fault_library,
)
from virtual_factory.faults.fault_models import (
    FaultConfig,
    FaultInstance,
    FaultLibrary,
    FaultSeverity,
    FaultSymptom,
    MaintenanceAction,
    RecoveryProfile,
)

__all__ = [
    "FaultEngine",
    "FaultScheduler",
    "FaultConfig",
    "FaultInstance",
    "FaultLibrary",
    "FaultSeverity",
    "FaultSymptom",
    "MaintenanceAction",
    "RecoveryProfile",
    "load_fault_library",
    "load_fault_libraries",
    "build_default_fault_library",
]
