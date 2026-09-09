"""G7 — Hierarchical Scenario / Run Control (platform-level run authority).

Additive, generic vNext run-control layer:

- :mod:`runcontrol.targets` — G1 hierarchical target resolution;
- :mod:`runcontrol.lifecycle` — run lifecycle service + immutable RunContextV2;
- :mod:`runcontrol.assy_bridge` — ASSY execution bridge (G5 federation + G4
  coordinator, natural boundaries only);
- :mod:`runcontrol.continuous_bridge` — continuous execution bridge
  (RuntimeService seam, root-only).

G7 owns run identity/lifecycle state ONLY; domain runtimes stay authoritative.
No universal timestep, no fractional ASSY dwell/index, no run-id reuse for
terminal runs, no fabricated replay inputs, no invented continuous hierarchy,
no G8+.
"""

from __future__ import annotations

from virtual_factory.runcontrol.assy_bridge import AssyExecutionBridge
from virtual_factory.runcontrol.continuous_bridge import (
    CONTINUOUS_WORKSPACE_ID,
    PROCESS_SCOPE_ID,
    ContinuousExecutionBridge,
    build_continuous_workspace,
    process_scope_path,
)
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
from virtual_factory.runcontrol.shwtp_bridge import ShwtpExecutionBridge
from virtual_factory.runcontrol.session import (
    RuntimeSession,
    SessionError,
    SessionIdentity,
    build_shwtp_session,
    build_tipa_session,
)

__all__ = [
    "AssyExecutionBridge",
    "CONTINUOUS_WORKSPACE_ID",
    "ContinuousExecutionBridge",
    "ExecutionBridge",
    "PROCESS_SCOPE_ID",
    "ReplayUnavailableError",
    "RunLifecycleError",
    "RunLifecycleService",
    "RunRecord",
    "RunState",
    "StepResult",
    "TargetResolution",
    "TargetResolutionError",
    "build_continuous_workspace",
    "process_scope_path",
    "resolve_target",
    "ShwtpExecutionBridge",
    "RuntimeSession",
    "SessionError",
    "SessionIdentity",
    "build_shwtp_session",
    "build_tipa_session",
]
