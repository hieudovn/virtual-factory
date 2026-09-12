"""VF-vNEXT-G15 — SH-WTP federated evaluation trace & diagnostics.

Smallest deterministic evaluation/diagnostic layer over the accepted G14B
federation (``ShwtpFederation``, explicit_lagged):

    T106 (LogicalOnly) -> REL-SHW-F01 / G14A projection -> T108 (FirstOrder)

This module is evaluation and diagnostics ONLY. It does NOT:

- change T106/T108 equations or standalone behavior;
- change G4 Coordinator / ExecutableParticipant / BoundaryTransfer semantics;
- change G14A projection identities or the F01 binding;
- change ``explicit_lagged`` semantics or G14B-C01 identity locking;
- invent a scheduler/profile engine or variable per-window scenario inputs;
- include T110 or F02-F07 execution, plant-wide execution, UI/alarms/KPIs;
- invent a global numeric tolerance policy;
- claim measured/site/calibrated/plant truth.

Evaluation model
---------------
One immutable/detached evaluation row is captured per COMPLETED window from the
actual T106/T108 runtime step records + the federation's committed inflow
(after the boundary commit). Mass-balance residual for every completed T108
step uses the accepted G13 equation::

    residual = V_end - (V_start + Qin_used*dt - Qout_applied*dt - overflow)

Under the accepted model this residual is EXACTLY ``0.0`` (the runtime's own
arithmetic guarantees it; see ``t108_mass_balance_residual``). A non-zero
residual would mean the accepted exact invariant was violated and fails closed.

Lag visibility: ``lag_windows = 1`` for ``explicit_lagged`` — window 1 uses the
explicit ``initial_t108_inflow_m3_s``; boundary 1 commits T106 output for the
next window; window 2 uses exactly that previous T106 output. This is
evaluation metadata for the current policy, NOT a ``CompositionGraph`` property.

Authority unchanged: ``vf_runtime_authorization = NOT_AUTHORIZED``,
``site_authorized_execution = NOT_AUTHORIZED``. Provenance preserved:
T106 = simulation/synthetic/logical_only; T108 = simulation/synthetic/first_order.
"""

from __future__ import annotations

from dataclasses import dataclass

from virtual_factory.shwtp.federation import (
    SHWTP_FEDERATION_COUPLING_POLICY,
    ShwtpFederation,
    ShwtpFederationConfig,
)
from virtual_factory.shwtp.runtime import T108Step

SHWTP_EVALUATION_LAG_WINDOWS = 1
SHWTP_EVALUATION_ROW_SCHEMA = "vf.vnext.g15.shwtp.evaluation_row.v1"
SHWTP_EVALUATION_SUMMARY_SCHEMA = "vf.vnext.g15.shwtp.evaluation_summary.v1"
SHWTP_EVALUATION_SERIALIZATION_SCHEMA = "vf.vnext.g15.shwtp.evaluation.v1"


class ShwtpEvaluationError(ValueError):
    """Raised when a SH-WTP evaluation invariant is violated (fail closed)."""


def t108_mass_balance_residual(step: T108Step) -> float:
    """Exact accepted-model mass-balance residual for one completed T108 step.

    ``residual = V_end - (V_start + Qin_used*dt - Qout_applied*dt - overflow)``

    Mirrors the accepted G13 runtime arithmetic exactly (dt == step interval),
    so the residual is exactly ``0.0`` — no tolerance policy is invented here.
    """
    if not isinstance(step, T108Step):
        raise ShwtpEvaluationError(
            f"step must be T108Step, got {type(step).__name__}"
        )
    dt = step.end_time_s - step.start_time_s
    recomputed = (
        step.start_volume_m3
        + step.inflow_m3_s * dt
        - step.applied_outflow_m3_s * dt
        - step.overflow_m3
    )
    return step.end_volume_m3 - recomputed


@dataclass(frozen=True, slots=True)
class ShwtpEvaluationRow:
    """One immutable/detached evaluation row per completed federation window.

    All numeric values are captured from the actual accepted runtime step
    records / federation committed state — never fabricated.
    """

    window_id: str
    window_index: int
    start_time_s: float
    end_time_s: float
    communication_step_s: float
    run_id: str
    coupling_policy: str
    # T106
    t106_input_flow_m3_s: float
    t106_output_staged_m3_s: float
    # T108
    t108_inflow_used_m3_s: float
    t108_committed_next_m3_s: float
    t108_requested_outflow_m3_s: float
    t108_applied_outflow_m3_s: float
    t108_start_volume_m3: float
    t108_end_volume_m3: float
    t108_end_level_m: float
    t108_overflow_m3: float
    mass_balance_residual_m3: float
    # provenance/fidelity/status references (truthful synthetic simulation)
    t106_origin_kind: str
    t106_data_status: str
    t106_fidelity: str
    t108_origin_kind: str
    t108_data_status: str
    t108_fidelity: str
    status: str

    def to_dict(self) -> dict:
        return {
            "schema": SHWTP_EVALUATION_ROW_SCHEMA,
            "window_id": self.window_id,
            "window_index": self.window_index,
            "start_time_s": self.start_time_s,
            "end_time_s": self.end_time_s,
            "communication_step_s": self.communication_step_s,
            "run_id": self.run_id,
            "coupling_policy": self.coupling_policy,
            "t106_input_flow_m3_s": self.t106_input_flow_m3_s,
            "t106_output_staged_m3_s": self.t106_output_staged_m3_s,
            "t108_inflow_used_m3_s": self.t108_inflow_used_m3_s,
            "t108_committed_next_m3_s": self.t108_committed_next_m3_s,
            "t108_requested_outflow_m3_s": self.t108_requested_outflow_m3_s,
            "t108_applied_outflow_m3_s": self.t108_applied_outflow_m3_s,
            "t108_start_volume_m3": self.t108_start_volume_m3,
            "t108_end_volume_m3": self.t108_end_volume_m3,
            "t108_end_level_m": self.t108_end_level_m,
            "t108_overflow_m3": self.t108_overflow_m3,
            "mass_balance_residual_m3": self.mass_balance_residual_m3,
            "t106_origin_kind": self.t106_origin_kind,
            "t106_data_status": self.t106_data_status,
            "t106_fidelity": self.t106_fidelity,
            "t108_origin_kind": self.t108_origin_kind,
            "t108_data_status": self.t108_data_status,
            "t108_fidelity": self.t108_fidelity,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class ShwtpEvaluationSummary:
    """Deterministic immutable summary derived only from the trace rows."""

    run_id: str
    window_count: int
    start_time_s: float
    end_time_s: float
    communication_step_s: float
    coupling_policy: str
    lag_windows: int
    t108_initial_volume_m3: float
    t108_final_volume_m3: float
    t108_min_volume_m3: float
    t108_max_volume_m3: float
    t108_initial_level_m: float
    t108_final_level_m: float
    total_t106_staged_volume_m3: float
    total_t108_inflow_used_volume_m3: float
    total_applied_outflow_volume_m3: float
    total_overflow_volume_m3: float
    max_abs_mass_balance_residual_m3: float

    def to_dict(self) -> dict:
        return {
            "schema": SHWTP_EVALUATION_SUMMARY_SCHEMA,
            "run_id": self.run_id,
            "window_count": self.window_count,
            "start_time_s": self.start_time_s,
            "end_time_s": self.end_time_s,
            "communication_step_s": self.communication_step_s,
            "coupling_policy": self.coupling_policy,
            "lag_windows": self.lag_windows,
            "t108_initial_volume_m3": self.t108_initial_volume_m3,
            "t108_final_volume_m3": self.t108_final_volume_m3,
            "t108_min_volume_m3": self.t108_min_volume_m3,
            "t108_max_volume_m3": self.t108_max_volume_m3,
            "t108_initial_level_m": self.t108_initial_level_m,
            "t108_final_level_m": self.t108_final_level_m,
            "total_t106_staged_volume_m3": self.total_t106_staged_volume_m3,
            "total_t108_inflow_used_volume_m3": self.total_t108_inflow_used_volume_m3,
            "total_applied_outflow_volume_m3": self.total_applied_outflow_volume_m3,
            "total_overflow_volume_m3": self.total_overflow_volume_m3,
            "max_abs_mass_balance_residual_m3": self.max_abs_mass_balance_residual_m3,
        }


class ShwtpEvaluator:
    """Bounded deterministic evaluation runner around ``ShwtpFederation``.

    One evaluator instance owns one fresh federation attempt. ``run()`` executes
    ``window_count`` windows sequentially (``window-1`` .. ``window-N``),
    capturing exactly one immutable row per COMPLETED window and then building
    the deterministic summary. A failed window fails closed (no retry, no
    rollback, no skip, no hiding). No scheduler/profile engine.
    """

    __slots__ = ("_config", "_window_count", "_federation", "_rows", "_summary")

    def __init__(
        self,
        config: ShwtpFederationConfig,
        *,
        window_count: int,
    ) -> None:
        if not isinstance(config, ShwtpFederationConfig):
            raise ShwtpEvaluationError(
                f"config must be ShwtpFederationConfig, "
                f"got {type(config).__name__}"
            )
        if isinstance(window_count, bool) or not isinstance(window_count, int):
            raise ShwtpEvaluationError(
                f"window_count must be an int, got {type(window_count).__name__}"
            )
        if window_count < 1:
            raise ShwtpEvaluationError(
                f"window_count must be >= 1, got {window_count!r}"
            )
        self._config = config
        self._window_count = window_count
        # A fresh evaluation owns a fresh federation attempt (isolated).
        self._federation = ShwtpFederation(config)
        self._rows: list[ShwtpEvaluationRow] = []
        self._summary: ShwtpEvaluationSummary | None = None

    # -- identity ----------------------------------------------------------
    @property
    def config(self) -> ShwtpFederationConfig:
        return self._config

    @property
    def window_count(self) -> int:
        return self._window_count

    @property
    def federation(self) -> ShwtpFederation:
        return self._federation

    @property
    def rows(self) -> tuple[ShwtpEvaluationRow, ...]:
        """Immutable ordered trace rows (only completed windows)."""
        return tuple(self._rows)

    @property
    def summary(self) -> ShwtpEvaluationSummary | None:
        """Deterministic summary; None until ``run()`` completes."""
        return self._summary

    # -- execution ---------------------------------------------------------
    def run(self) -> "ShwtpEvaluator":
        """Execute window-1..window-N sequentially; fail closed on any failure."""
        if self._rows:
            raise ShwtpEvaluationError("evaluation already ran; fresh attempt required")
        for index in range(1, self._window_count + 1):
            window_id = f"window-{index}"
            outcome = self._federation.run_window(window_id)
            if outcome.status != "completed":
                raise ShwtpEvaluationError(
                    f"window {window_id} failed closed: {outcome.failure}; "
                    f"no retry/rollback/skip/hide in evaluation"
                )
            self._rows.append(self._capture_row(index, window_id, outcome.window_id))
        self._summary = self._build_summary()
        return self

    def _capture_row(
        self, index: int, window_id: str, outcome_window_id: str
    ) -> ShwtpEvaluationRow:
        # Trace identity must match the federation run/workspace/policy.
        if outcome_window_id != window_id:
            raise ShwtpEvaluationError(
                f"trace window {window_id!r} does not match federation outcome "
                f"window {outcome_window_id!r}"
            )
        if self._federation.coupling_policy != SHWTP_FEDERATION_COUPLING_POLICY:
            raise ShwtpEvaluationError(
                f"unsupported coupling policy "
                f"{self._federation.coupling_policy!r}"
            )
        if self._config.run_id != self._federation.config.run_id:
            raise ShwtpEvaluationError(
                "evaluation run_id does not match federation run_id"
            )

        t106 = self._federation.t106
        t108 = self._federation.t108
        t106_step = t106.last_step
        t108_step = t108.last_step
        if t106_step is None or t108_step is None:
            raise ShwtpEvaluationError(
                f"missing T106/T108 step record after completed window {window_id}"
            )

        dt = self._config.communication_step_s
        if (
            t108_step.end_time_s - t108_step.start_time_s != dt
            or t106_step.end_time_s - t106_step.start_time_s != dt
        ):
            raise ShwtpEvaluationError(
                f"window {window_id} step interval does not match "
                f"communication_step_s {dt!r}"
            )

        # Exact accepted-model mass-balance invariant (no invented tolerance).
        residual = t108_mass_balance_residual(t108_step)
        if residual != 0.0:
            raise ShwtpEvaluationError(
                f"mass-balance residual {residual!r} violates the accepted "
                f"exact invariant for window {window_id}"
            )

        # Provenance/fidelity refs must be the truthful synthetic labels.
        t106_fidelity = t106_step.provenance.fidelity
        t108_fidelity = t108_step.provenance.fidelity
        t106_data = t106_step.provenance.data_status
        t108_data = t108_step.provenance.data_status
        t106_origin = t106_step.provenance.origin_kind
        t108_origin = t108_step.provenance.origin_kind

        return ShwtpEvaluationRow(
            window_id=window_id,
            window_index=index,
            start_time_s=t108_step.start_time_s,
            end_time_s=t108_step.end_time_s,
            communication_step_s=dt,
            run_id=self._config.run_id,
            coupling_policy=self._federation.coupling_policy,
            t106_input_flow_m3_s=t106_step.inflow_m3_s,
            t106_output_staged_m3_s=t106_step.output_flow_m3_s,
            t108_inflow_used_m3_s=t108_step.inflow_m3_s,
            t108_committed_next_m3_s=t108.committed_inflow_m3_s,
            t108_requested_outflow_m3_s=t108_step.requested_outflow_m3_s,
            t108_applied_outflow_m3_s=t108_step.applied_outflow_m3_s,
            t108_start_volume_m3=t108_step.start_volume_m3,
            t108_end_volume_m3=t108_step.end_volume_m3,
            t108_end_level_m=t108_step.end_level_m,
            t108_overflow_m3=t108_step.overflow_m3,
            mass_balance_residual_m3=residual,
            t106_origin_kind=t106_origin.value,
            t106_data_status=t106_data.value,
            t106_fidelity=t106_fidelity.value,
            t108_origin_kind=t108_origin.value,
            t108_data_status=t108_data.value,
            t108_fidelity=t108_fidelity.value,
            status="completed",
        )

    def _build_summary(self) -> ShwtpEvaluationSummary:
        rows = self._rows
        if not rows:
            raise ShwtpEvaluationError(
                "cannot build a summary with zero completed windows"
            )
        dt = self._config.communication_step_s
        initial_volume = rows[0].t108_start_volume_m3
        final_volume = rows[-1].t108_end_volume_m3
        volumes = [r.t108_start_volume_m3 for r in rows]
        volumes.extend(r.t108_end_volume_m3 for r in rows)
        area = self._federation.t108.runtime.config.tank_area_m2

        total_t106_staged = sum(r.t106_output_staged_m3_s * dt for r in rows)
        total_inflow_used = sum(r.t108_inflow_used_m3_s * dt for r in rows)
        total_applied = sum(r.t108_applied_outflow_m3_s * dt for r in rows)
        total_overflow = sum(r.t108_overflow_m3 for r in rows)
        max_abs_residual = max(
            abs(r.mass_balance_residual_m3) for r in rows
        )

        return ShwtpEvaluationSummary(
            run_id=self._config.run_id,
            window_count=len(rows),
            start_time_s=rows[0].start_time_s,
            end_time_s=rows[-1].end_time_s,
            communication_step_s=dt,
            coupling_policy=self._federation.coupling_policy,
            lag_windows=SHWTP_EVALUATION_LAG_WINDOWS,
            t108_initial_volume_m3=initial_volume,
            t108_final_volume_m3=final_volume,
            t108_min_volume_m3=min(volumes),
            t108_max_volume_m3=max(volumes),
            t108_initial_level_m=initial_volume / area,
            t108_final_level_m=final_volume / area,
            total_t106_staged_volume_m3=total_t106_staged,
            total_t108_inflow_used_volume_m3=total_inflow_used,
            total_applied_outflow_volume_m3=total_applied,
            total_overflow_volume_m3=total_overflow,
            max_abs_mass_balance_residual_m3=max_abs_residual,
        )

    def serialize(self) -> dict:
        """Deterministic full evaluation inspection (rows + summary)."""
        return {
            "schema": SHWTP_EVALUATION_SERIALIZATION_SCHEMA,
            "run_id": self._config.run_id,
            "window_count": self._window_count,
            "coupling_policy": self._federation.coupling_policy,
            "lag_windows": SHWTP_EVALUATION_LAG_WINDOWS,
            "completed_windows": len(self._rows),
            "rows": [r.to_dict() for r in self._rows],
            "summary": (
                self._summary.to_dict() if self._summary is not None else None
            ),
        }
