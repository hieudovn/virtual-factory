"""VF-vNEXT-G13 — SH-WTP T108 standalone synthetic first-order tank runtime.

Implements ONLY the first authorized SH-WTP executable slice:

- canonical id  : ``UNIT-SHW-L1-T108``
- VF StructuralPath : ``shwtp/line1/l1_t108``
- behavior       : standalone synthetic/reference first-order tank accumulator.

Frozen authority (G12C, ``shwtp_synthetic_runtime_admission.json``):

- ``review_status = COMPLETE`` / ``authorization_mode = CANDIDATE_SCOPED``;
- first authorized slice = T108; T106 allowed only later/optional; T110 blocked;
- ``vf_runtime_authorization = NOT_AUTHORIZED``;
- ``site_authorized_execution = NOT_AUTHORIZED``.

This module is an isolated, reversible SH-WTP runtime seam. It does NOT:

- implement T106 or T110;
- project G12A/B reference relations (``FLOWS_TO`` / ``DISCHARGES_TO`` /
  ``CONNECTED_TO``) into ``BoundaryPort`` / G4 ``CompositionBinding`` / runtime
  port direction / coordinator ordering — T108 inflow/outflow are standalone
  scenario/config boundary values;
- enable ``shwtp`` or ``shwtp/line1`` as executable multi-scope targets (only
  the exact ``shwtp/line1/l1_t108`` scope is runnable here);
- touch legacy ``equipment.process_dynamics`` or the continuous engine;
- claim measured/site truth: every output carries provenance
  ``origin=simulation``, ``data_status=synthetic``, ``fidelity=first_order``.

Step semantics (one deterministic step of duration ``dt_s``):

    available        = volume + inflow * dt
    applied_outflow  = min(requested_outflow, available / dt)
    pre_overflow     = available - applied_outflow * dt
    overflow_m3      = max(0, pre_overflow - capacity)
    next_volume      = pre_overflow - overflow_m3
    next_level       = next_volume / tank_area_m2

Mass-balance invariant per step::

    V_next = V_prev + Qin*dt - Qout_applied*dt - overflow_m3

Empty-tank demand is limited by available inventory (never negative volume);
overflow is explicit and never silently discarded.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from virtual_factory.provenance import (
    DataStatus,
    Fidelity,
    OriginKind,
    ProvenanceV2,
    RunContextV2,
    to_provenance_v2,
)
from virtual_factory.shwtp.structural import SHWTP_WORKSPACE_ID
from virtual_factory.workspace import StructuralPath

SHWTP_T108_CANONICAL_ID = "UNIT-SHW-L1-T108"
SHWTP_T108_SCOPE_PATH = StructuralPath(("shwtp", "line1", "l1_t108"))


class T108RuntimeError(ValueError):
    """Raised when a T108 runtime invariant is violated (fail closed)."""


def _require_number(value, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise T108RuntimeError(f"{name} must be a finite number, got {value!r}")
    if not math.isfinite(float(value)):
        raise T108RuntimeError(f"{name} must be a finite number, got {value!r}")


@dataclass(frozen=True, slots=True)
class T108Config:
    """Explicit scenario/config inputs for one T108 tank attempt.

    All behavior-affecting values are required (no hidden defaults). These are
    VF synthetic scenario/config assumptions, never relabeled plant parameters.
    """

    capacity_m3: float
    tank_area_m2: float
    initial_volume_m3: float
    dt_s: float

    def __post_init__(self) -> None:
        _require_number(self.capacity_m3, "capacity_m3")
        _require_number(self.tank_area_m2, "tank_area_m2")
        _require_number(self.initial_volume_m3, "initial_volume_m3")
        _require_number(self.dt_s, "dt_s")
        if self.capacity_m3 <= 0:
            raise T108RuntimeError("capacity_m3 must be > 0")
        if self.tank_area_m2 <= 0:
            raise T108RuntimeError("tank_area_m2 must be > 0")
        if self.dt_s <= 0:
            raise T108RuntimeError("dt_s must be > 0")
        if not (0.0 <= self.initial_volume_m3 <= self.capacity_m3):
            raise T108RuntimeError(
                "initial_volume_m3 must satisfy 0 <= initial_volume_m3 <= capacity_m3"
            )


@dataclass(frozen=True, slots=True)
class T108State:
    """Immutable/detached point-in-time state snapshot."""

    time_s: float
    volume_m3: float
    level_m: float


@dataclass(frozen=True, slots=True)
class T108Step:
    """Immutable/detached record of one deterministic step.

    Carries start state, explicit inputs, computed outputs, end state, and the
    truthful synthetic first-order provenance envelope.
    """

    canonical_id: str
    scope_path: str
    step_index: int
    start_time_s: float
    start_volume_m3: float
    inflow_m3_s: float
    requested_outflow_m3_s: float
    applied_outflow_m3_s: float
    overflow_m3: float
    end_time_s: float
    end_volume_m3: float
    end_level_m: float
    provenance: ProvenanceV2


class T108TankRuntime:
    """Standalone synthetic first-order tank accumulator for ``shwtp/line1/l1_t108``.

    One runtime instance is one isolated execution attempt. Attempts do not share
    mutable state. ``step`` advances this attempt exactly one ``dt_s``; ``reset``
    restores the same attempt to its initial state; ``snapshot`` returns a
    detached immutable state.
    """

    __slots__ = (
        "_config",
        "_run_context",
        "_canonical_id",
        "_time_s",
        "_volume_m3",
        "_step_index",
        "_semantic_contract_version",
        "_semantic_contract_sha",
    )

    def __init__(
        self,
        config: T108Config,
        run_context: RunContextV2,
        *,
        canonical_id: str = SHWTP_T108_CANONICAL_ID,
        semantic_contract_version: str | None = None,
        semantic_contract_sha: str | None = None,
    ) -> None:
        if not isinstance(config, T108Config):
            raise T108RuntimeError(
                f"config must be T108Config, got {type(config).__name__}"
            )
        if not isinstance(run_context, RunContextV2):
            raise T108RuntimeError(
                f"run_context must be RunContextV2, got {type(run_context).__name__}"
            )
        if run_context.workspace_id != SHWTP_WORKSPACE_ID:
            raise T108RuntimeError(
                f"T108 runtime requires workspace {SHWTP_WORKSPACE_ID!r}, "
                f"got {run_context.workspace_id!r}"
            )
        if run_context.scope_path != SHWTP_T108_SCOPE_PATH:
            raise T108RuntimeError(
                f"T108 runtime only runs the exact target "
                f"{SHWTP_T108_SCOPE_PATH.as_string()!r}, got "
                f"{run_context.scope_path.as_string() if run_context.scope_path is not None else None!r}. "
                f"Workspace/container targets (shwtp, shwtp/line1) are NOT executable here."
            )

        self._config = config
        self._run_context = run_context
        self._canonical_id = canonical_id
        self._time_s = 0.0
        self._volume_m3 = config.initial_volume_m3
        self._step_index = 0
        self._semantic_contract_version = semantic_contract_version
        self._semantic_contract_sha = semantic_contract_sha

    # -- identity -----------------------------------------------------------
    @property
    def canonical_id(self) -> str:
        """Read-only PIM canonical semantic reference (never runtime identity)."""
        return self._canonical_id

    @property
    def scope_path(self) -> StructuralPath:
        return SHWTP_T108_SCOPE_PATH

    @property
    def config(self) -> T108Config:
        return self._config

    @property
    def run_context(self) -> RunContextV2:
        return self._run_context

    @property
    def step_index(self) -> int:
        return self._step_index

    # -- state --------------------------------------------------------------
    @property
    def state(self) -> T108State:
        """Detached immutable state snapshot (time, volume, level)."""
        return T108State(
            time_s=self._time_s,
            volume_m3=self._volume_m3,
            level_m=self._volume_m3 / self._config.tank_area_m2,
        )

    def snapshot(self) -> T108State:
        return self.state

    # -- lifecycle ----------------------------------------------------------
    def step(self, inflow_m3_s: float, requested_outflow_m3_s: float) -> T108Step:
        """Advance exactly one ``dt_s`` with explicit scenario boundary values.

        Fails closed on negative (or non-finite) inflow/outflow requests.
        """
        _require_number(inflow_m3_s, "inflow_m3_s")
        _require_number(requested_outflow_m3_s, "requested_outflow_m3_s")
        if inflow_m3_s < 0:
            raise T108RuntimeError("inflow_m3_s must be >= 0")
        if requested_outflow_m3_s < 0:
            raise T108RuntimeError("requested_outflow_m3_s must be >= 0")

        dt = self._config.dt_s
        capacity = self._config.capacity_m3
        area = self._config.tank_area_m2

        v_prev = self._volume_m3
        t_prev = self._time_s

        available = v_prev + inflow_m3_s * dt
        applied_outflow = min(requested_outflow_m3_s, available / dt)
        pre_overflow = available - applied_outflow * dt
        overflow = max(0.0, pre_overflow - capacity)
        v_next = pre_overflow - overflow
        level_next = v_next / area
        t_next = t_prev + dt

        # Fail-closed mass-balance invariant.
        recomputed = v_prev + inflow_m3_s * dt - applied_outflow * dt - overflow
        if not math.isclose(recomputed, v_next, rel_tol=1e-9, abs_tol=1e-12):
            raise T108RuntimeError(
                f"mass-balance invariant violated: recomputed={recomputed!r} "
                f"next_volume={v_next!r}"
            )

        provenance = to_provenance_v2(
            self._run_context,
            origin_kind=OriginKind.SIMULATION,
            fidelity=Fidelity.FIRST_ORDER,
            data_status=DataStatus.SYNTHETIC,
            semantic_contract_version=self._semantic_contract_version,
            semantic_contract_sha=self._semantic_contract_sha,
            evidence_note=(
                "SH-WTP T108 standalone synthetic first-order tank accumulator"
            ),
            simulation_time_s=t_next,
            step=self._step_index,
        )

        record = T108Step(
            canonical_id=self._canonical_id,
            scope_path=SHWTP_T108_SCOPE_PATH.as_string(),
            step_index=self._step_index,
            start_time_s=t_prev,
            start_volume_m3=v_prev,
            inflow_m3_s=inflow_m3_s,
            requested_outflow_m3_s=requested_outflow_m3_s,
            applied_outflow_m3_s=applied_outflow,
            overflow_m3=overflow,
            end_time_s=t_next,
            end_volume_m3=v_next,
            end_level_m=level_next,
            provenance=provenance,
        )

        self._time_s = t_next
        self._volume_m3 = v_next
        self._step_index += 1
        return record

    def reset(self) -> None:
        """Reset this same attempt to its initial state (time=0, initial volume)."""
        self._time_s = 0.0
        self._volume_m3 = self._config.initial_volume_m3
        self._step_index = 0
