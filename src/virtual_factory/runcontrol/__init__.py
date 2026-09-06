"""G7 — Hierarchical Scenario / Run Control (platform-level run authority).

Additive, generic vNext run-control layer:

- :mod:`runcontrol.targets` — G1 hierarchical target resolution;
- :mod:`runcontrol.lifecycle` — run lifecycle service + immutable RunContextV2;
- :mod:`runcontrol.assy_bridge` — ASSY execution bridge (G5 federation + G4
  coordinator, natural boundaries only).

G7 owns run identity/lifecycle state ONLY; domain runtimes stay authoritative.
No universal timestep, no fractional ASSY dwell/index, no run-id reuse for
terminal runs, no fabricated replay inputs, no G8+.
"""

from __future__ import annotations

from virtual_factory.runcontrol.assy_bridge import AssyExecutionBridge
from virtual_factory.runcontrol.lifecycle import (
    ExecutionBridge,
    ReplayUnavailableError,
    RunLifecycleError,
    RunLifecycleService,
    RunRecord,
    RunState,
    StepResult,
)
from virtual_factory.runcontrol.targets import (
    TargetResolution,
    TargetResolutionError,
    resolve_target,
)

__all__ = [
    "AssyExecutionBridge",
    "ExecutionBridge",
    "ReplayUnavailableError",
    "RunLifecycleError",
    "RunLifecycleService",
    "RunRecord",
    "RunState",
    "StepResult",
    "TargetResolution",
    "TargetResolutionError",
    "resolve_target",
]
