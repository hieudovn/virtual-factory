"""VF-vNEXT-G13B — SH-WTP T106 standalone synthetic LogicalOnly runtime.

Implements ONLY the second already-authorized SH-WTP executable candidate:

- canonical id  : ``UNIT-SHW-L1-T106`` (locked read-only PIM semantic reference)
- VF StructuralPath : ``shwtp/line1/l1_t106``
- behavior       : standalone synthetic LogicalOnly zero-storage pass-through.

Frozen authority (G12C, ``shwtp_synthetic_runtime_admission.json``):

- ``review_status = COMPLETE`` / ``authorization_mode = CANDIDATE_SCOPED``;
- T106 = ``SYNTHETIC_REFERENCE_ALLOWED`` (LogicalOnly ceiling);
- T108 remains the accepted first-order standalone runtime (G13, unchanged);
- T110 remains ``BLOCKED_PENDING_EVIDENCE``;
- ``vf_runtime_authorization = NOT_AUTHORIZED``;
- ``site_authorized_execution = NOT_AUTHORIZED``.

Exact LogicalOnly contract: zero-storage logical pass-through black box.

- Explicit per-step input ``inflow_m3_s >= 0``.
- Explicit config ``dt_s > 0``.
- ``output_flow_m3_s = input_flow_m3_s``; simulation time advances by ``dt_s``.
- No attenuation, delay, capacity, efficiency, pressure, quality transformation,
  accumulation, filter state, backwash state, or hidden default behavior.

This module does NOT:

- implement filtration physics / headloss / quality / backwash / storage;
- wire T106 -> T108 or project G12A/B relations into runtime connections;
- enable ``shwtp`` / ``shwtp/line1`` / T110 / multi-scope execution (only the
  exact ``shwtp/line1/l1_t106`` scope is runnable here);
- modify T108 runtime or the legacy continuous engine;
- claim measured/site truth: every output carries provenance
  ``origin=simulation``, ``data_status=synthetic``, ``fidelity=logical_only``.
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

SHWTP_T106_CANONICAL_ID = "UNIT-SHW-L1-T106"
SHWTP_T106_SCOPE_PATH = StructuralPath(("shwtp", "line1", "l1_t106"))


class T106RuntimeError(ValueError):
    """Raised when a T106 runtime invariant is violated (fail closed)."""


def _require_number(value, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise T106RuntimeError(f"{name} must be a finite number, got {value!r}")
    if not math.isfinite(float(value)):
        raise T106RuntimeError(f"{name} must be a finite number, got {value!r}")


@dataclass(frozen=True, slots=True)
class T106Config:
    """Explicit scenario/config input for one T106 logical attempt.

    ``dt_s`` is the deterministic step duration. There are no hidden
    behavior-affecting defaults.
    """

    dt_s: float

    def __post_init__(self) -> None:
        _require_number(self.dt_s, "dt_s")
        if self.dt_s <= 0:
            raise T106RuntimeError("dt_s must be > 0")


@dataclass(frozen=True, slots=True)
class T106State:
    """Immutable/detached point-in-time state snapshot.

    Carries truthful G2 provenance (``simulation`` / ``synthetic`` /
    ``logical_only``) so the detached snapshot visibly distinguishes synthetic
    LogicalOnly VF truth from site truth.
    """

    time_s: float
    last_input_flow_m3_s: float
    last_output_flow_m3_s: float
    provenance: ProvenanceV2


@dataclass(frozen=True, slots=True)
class T106Step:
    """Immutable/detached record of one deterministic logical step."""

    canonical_id: str
    scope_path: str
    step_index: int
    start_time_s: float
    inflow_m3_s: float
    output_flow_m3_s: float
    end_time_s: float
    provenance: ProvenanceV2


class T106LogicalRuntime:
    """Standalone synthetic LogicalOnly pass-through for ``shwtp/line1/l1_t106``.

    One runtime instance is one isolated execution attempt. Attempts do not
    share mutable state. ``step`` advances exactly one ``dt_s``; ``reset``
    restores the same attempt to its initial logical state; ``snapshot`` returns
    a detached immutable state.
    """

    __slots__ = (
        "_config",
        "_run_context",
        "_time_s",
        "_last_input",
        "_last_output",
        "_step_index",
        "_semantic_contract_version",
        "_semantic_contract_sha",
    )

    def __init__(
        self,
        config: T106Config,
        run_context: RunContextV2,
        *,
        semantic_contract_version: str | None = None,
        semantic_contract_sha: str | None = None,
    ) -> None:
        if not isinstance(config, T106Config):
            raise T106RuntimeError(
                f"config must be T106Config, got {type(config).__name__}"
            )
        if not isinstance(run_context, RunContextV2):
            raise T106RuntimeError(
                f"run_context must be RunContextV2, got {type(run_context).__name__}"
            )
        if run_context.workspace_id != SHWTP_WORKSPACE_ID:
            raise T106RuntimeError(
                f"T106 runtime requires workspace {SHWTP_WORKSPACE_ID!r}, "
                f"got {run_context.workspace_id!r}"
            )
        if run_context.scope_path != SHWTP_T106_SCOPE_PATH:
            raise T106RuntimeError(
                f"T106 runtime only runs the exact target "
                f"{SHWTP_T106_SCOPE_PATH.as_string()!r}, got "
                f"{run_context.scope_path.as_string() if run_context.scope_path is not None else None!r}. "
                f"Workspace/container targets (shwtp, shwtp/line1) and T108/T110 "
                f"are NOT executable here."
            )

        self._config = config
        self._run_context = run_context
        self._time_s = 0.0
        self._last_input = 0.0
        self._last_output = 0.0
        self._step_index = 0
        self._semantic_contract_version = semantic_contract_version
        self._semantic_contract_sha = semantic_contract_sha

    # -- identity -----------------------------------------------------------
    @property
    def canonical_id(self) -> str:
        """Locked read-only PIM canonical semantic reference (never VF identity)."""
        return SHWTP_T106_CANONICAL_ID

    @property
    def scope_path(self) -> StructuralPath:
        return SHWTP_T106_SCOPE_PATH

    @property
    def config(self) -> T106Config:
        return self._config

    @property
    def run_context(self) -> RunContextV2:
        return self._run_context

    @property
    def step_index(self) -> int:
        return self._step_index

    # -- state --------------------------------------------------------------
    @property
    def state(self) -> T106State:
        """Detached immutable state snapshot with truthful G2 provenance."""
        return T106State(
            time_s=self._time_s,
            last_input_flow_m3_s=self._last_input,
            last_output_flow_m3_s=self._last_output,
            provenance=self._state_provenance(),
        )

    def _state_provenance(self) -> ProvenanceV2:
        return to_provenance_v2(
            self._run_context,
            origin_kind=OriginKind.SIMULATION,
            fidelity=Fidelity.LOGICAL_ONLY,
            data_status=DataStatus.SYNTHETIC,
            semantic_contract_version=self._semantic_contract_version,
            semantic_contract_sha=self._semantic_contract_sha,
            evidence_note="SH-WTP T106 standalone synthetic LogicalOnly pass-through",
            simulation_time_s=self._time_s,
            step=self._step_index,
        )

    def snapshot(self) -> T106State:
        return self.state

    # -- lifecycle ----------------------------------------------------------
    def step(self, inflow_m3_s: float) -> T106Step:
        """Advance exactly one ``dt_s`` with an explicit scenario inflow.

        LogicalOnly pass-through: ``output_flow = inflow``. Fails closed on
        negative or non-finite inflow.
        """
        _require_number(inflow_m3_s, "inflow_m3_s")
        if inflow_m3_s < 0:
            raise T106RuntimeError("inflow_m3_s must be >= 0")

        dt = self._config.dt_s
        t_prev = self._time_s
        t_next = t_prev + dt
        output = inflow_m3_s

        provenance = to_provenance_v2(
            self._run_context,
            origin_kind=OriginKind.SIMULATION,
            fidelity=Fidelity.LOGICAL_ONLY,
            data_status=DataStatus.SYNTHETIC,
            semantic_contract_version=self._semantic_contract_version,
            semantic_contract_sha=self._semantic_contract_sha,
            evidence_note="SH-WTP T106 standalone synthetic LogicalOnly pass-through",
            simulation_time_s=t_next,
            step=self._step_index,
        )

        record = T106Step(
            canonical_id=SHWTP_T106_CANONICAL_ID,
            scope_path=SHWTP_T106_SCOPE_PATH.as_string(),
            step_index=self._step_index,
            start_time_s=t_prev,
            inflow_m3_s=inflow_m3_s,
            output_flow_m3_s=output,
            end_time_s=t_next,
            provenance=provenance,
        )

        self._time_s = t_next
        self._last_input = inflow_m3_s
        self._last_output = output
        self._step_index += 1
        return record

    def reset(self) -> None:
        """Reset this same attempt to its initial logical state."""
        self._time_s = 0.0
        self._last_input = 0.0
        self._last_output = 0.0
        self._step_index = 0
