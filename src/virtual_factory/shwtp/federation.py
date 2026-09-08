"""VF-vNEXT-G14B — SH-WTP T106->T108 explicit lagged federation (F01 only).

Executes the already-authorized two-scope federation:

    T106 (LogicalOnly) --REL-SHW-F01 / G14A projection--> T108 (FirstOrder)

using the existing G4 ``Coordinator`` / ``ExecutableParticipant`` /
``BoundaryTransfer`` semantics. The two accepted standalone runtimes
(T106 from G13B, T108 from G13/G13-C01) are wrapped — never modified — by the
smallest SH-WTP-specific participant adapters.

Coupling policy (frozen SA decision):

    ``explicit_lagged``  (Jacobi-style one-window-lag coupling)

This policy is an ORCHESTRATION policy exposed only at this SH-WTP federation
layer. It is deliberately NOT a property/semantic of ``CompositionGraph``,
``BoundaryPort``, ``CompositionBinding``, T106, or T108. Future gates may add
sequential/Gauss-Seidel, iterative, adaptive, or multirate policies above the
unchanged composition graph without touching G14A identities.

Exact one-window-lag semantics (boundaries t0=0, t1=h, t2=2h):

    Before window 1: T108 committed inflow = explicit ``initial_t108_inflow_m3_s``.
    Window 1 (0 -> h):  T106 produces Q106[1]; T108 advances with the INITIAL
                        inflow; after both advance, Q106[1] is committed to T108.
    Window 2 (h -> 2h): T108 advances with exactly Q106[1]; T106 produces
                        Q106[2]; after boundary 2, Q106[2] becomes window 3 input.

No same-window feed-through. No same-window retroactive re-step of T108.

Communication window baseline (G14B baseline constraint ONLY, not a universal
VF rule): one explicit shared ``communication_step_s > 0`` with

    T106Config.dt_s == T108Config.dt_s == communication_step_s

No multirate interpolation/substepping is implemented.

Frozen authority remains unchanged:

    vf_runtime_authorization   = NOT_AUTHORIZED
    site_authorized_execution  = NOT_AUTHORIZED

G14B authorizes only this bounded two-scope synthetic/reference federation
evaluation path.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Sequence

from virtual_factory.composition import (
    BoundaryTransfer,
    Coordinator,
    WindowOutcome,
)
from virtual_factory.provenance import RunContextV2
from virtual_factory.shwtp.logical_runtime import (
    SHWTP_T106_SCOPE_PATH,
    T106Config,
    T106LogicalRuntime,
    T106Step,
)
from virtual_factory.shwtp.projection import (
    SHWTP_F01_BINDING_ID,
    ShwtpF01Projection,
    build_shwtp_f01_projection,
    t106_out_port_ref,
    t108_in_port_ref,
)
from virtual_factory.shwtp.runtime import (
    SHWTP_T108_SCOPE_PATH,
    T108Config,
    T108Step,
    T108TankRuntime,
)
from virtual_factory.shwtp.structural import (
    SHWTP_WORKSPACE_ID,
    ShwtpWorkspace,
    build_shwtp_workspace,
)
from virtual_factory.workspace import StructuralPath

# --- Frozen G14B federation pins ---------------------------------------------
SHWTP_FEDERATION_COUPLING_POLICY = "explicit_lagged"
SHWTP_FEDERATION_PAYLOAD_KEY = "volumetric_flow_m3_s"
SHWTP_FEDERATION_TRANSFER_PREFIX = "XFER-SHW-F01"
SHWTP_FEDERATION_WINDOW_PREFIX = "window-"
SHWTP_FEDERATION_WINDOW_RE = re.compile(r"window-[1-9][0-9]*\Z")
SHWTP_FEDERATION_DEFAULT_RUN_ID = "run-shwtp-f01"


class ShwtpFederationError(ValueError):
    """Raised when a SH-WTP federation invariant is violated (fail closed)."""


def _require_number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ShwtpFederationError(
            f"{name} must be a finite number, got {value!r}"
        )
    if not math.isfinite(float(value)):
        raise ShwtpFederationError(
            f"{name} must be a finite number, got {value!r}"
        )
    return float(value)


def _require_nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ShwtpFederationError(f"{name} must be a non-empty str")
    return value


@dataclass(frozen=True, slots=True)
class ShwtpFederationConfig:
    """Explicit scenario/config inputs for one G14B federation evaluation.

    All behavior-affecting values are required (no hidden defaults). These are
    VF synthetic scenario/config assumptions, never relabeled plant parameters.
    """

    communication_step_s: float
    initial_t108_inflow_m3_s: float
    t106_inflow_m3_s: float
    t108_requested_outflow_m3_s: float
    t108_capacity_m3: float
    t108_tank_area_m2: float
    t108_initial_volume_m3: float
    coupling_policy: str = SHWTP_FEDERATION_COUPLING_POLICY
    run_id: str = SHWTP_FEDERATION_DEFAULT_RUN_ID

    def __post_init__(self) -> None:
        _require_number(self.communication_step_s, "communication_step_s")
        _require_number(self.initial_t108_inflow_m3_s, "initial_t108_inflow_m3_s")
        _require_number(self.t106_inflow_m3_s, "t106_inflow_m3_s")
        _require_number(
            self.t108_requested_outflow_m3_s, "t108_requested_outflow_m3_s"
        )
        _require_number(self.t108_capacity_m3, "t108_capacity_m3")
        _require_number(self.t108_tank_area_m2, "t108_tank_area_m2")
        _require_number(self.t108_initial_volume_m3, "t108_initial_volume_m3")

        if self.communication_step_s <= 0:
            raise ShwtpFederationError("communication_step_s must be > 0")
        if self.initial_t108_inflow_m3_s < 0:
            raise ShwtpFederationError("initial_t108_inflow_m3_s must be >= 0")
        if self.t106_inflow_m3_s < 0:
            raise ShwtpFederationError("t106_inflow_m3_s must be >= 0")
        if self.t108_requested_outflow_m3_s < 0:
            raise ShwtpFederationError(
                "t108_requested_outflow_m3_s must be >= 0"
            )
        if self.t108_capacity_m3 <= 0:
            raise ShwtpFederationError("t108_capacity_m3 must be > 0")
        if self.t108_tank_area_m2 <= 0:
            raise ShwtpFederationError("t108_tank_area_m2 must be > 0")
        if not (0.0 <= self.t108_initial_volume_m3 <= self.t108_capacity_m3):
            raise ShwtpFederationError(
                "t108_initial_volume_m3 must satisfy "
                "0 <= initial_volume_m3 <= capacity_m3"
            )

        # Unsupported orchestration policy must fail closed. Only the frozen
        # SA baseline policy is authorized in G14B.
        if self.coupling_policy != SHWTP_FEDERATION_COUPLING_POLICY:
            raise ShwtpFederationError(
                f"unsupported coupling policy {self.coupling_policy!r}; "
                f"only {SHWTP_FEDERATION_COUPLING_POLICY!r} is authorized in G14B"
            )
        _require_nonempty(self.run_id, "run_id")

    @property
    def t106_dt_s(self) -> float:
        """G14B baseline constraint: T106 dt == communication step."""
        return self.communication_step_s

    @property
    def t108_dt_s(self) -> float:
        """G14B baseline constraint: T108 dt == communication step."""
        return self.communication_step_s


def _validate_window_id(window_id: str) -> str:
    """Strict G14B window identity format (fail closed)."""
    _require_nonempty(window_id, "window_id")
    if not SHWTP_FEDERATION_WINDOW_RE.fullmatch(window_id):
        raise ShwtpFederationError(
            f"invalid window identity {window_id!r}; expected format "
            f"'window-<n>' with n >= 1"
        )
    return window_id


def _exact_boundary_check(
    current: float, target: float, dt_s: float, label: str
) -> None:
    """One communication window advances time by exactly ``dt_s``.

    No substepping, no multirate interpolation, no tolerance policy (matches G4).
    """
    if isinstance(target, bool) or not isinstance(target, (int, float)):
        raise ShwtpFederationError(
            f"{label} advance_to target must be numeric, got {target!r}"
        )
    if not math.isfinite(float(target)):
        raise ShwtpFederationError(f"{label} advance_to target must be finite")
    if target < current:
        raise ShwtpFederationError(
            f"{label} cannot advance backward: current {current!r} -> "
            f"target {target!r}"
        )
    if target != current + dt_s:
        raise ShwtpFederationError(
            f"{label} must advance exactly one communication step "
            f"{dt_s!r}: current {current!r} -> target {target!r} "
            f"(multirate/substepping is not authorized in G14B)"
        )


class ShwtpT106Participant:
    """G4 participant adapter around the accepted T106 standalone runtime.

    Each authorized window advances T106 exactly one communication step with an
    explicit synthetic inflow and stages exactly one detached ``BoundaryTransfer``
    on the G14A F01 binding. T106 is a pure source: any inbound transfer fails
    closed.
    """

    __slots__ = (
        "_runtime",
        "_inflow_m3_s",
        "_run_id",
        "_workspace_id",
        "_active_window_id",
        "_last_step",
        "_last_transfer",
    )

    def __init__(
        self,
        runtime: T106LogicalRuntime,
        inflow_m3_s: float,
        run_id: str,
        workspace_id: str = SHWTP_WORKSPACE_ID,
    ) -> None:
        if not isinstance(runtime, T106LogicalRuntime):
            raise ShwtpFederationError(
                f"runtime must be T106LogicalRuntime, "
                f"got {type(runtime).__name__}"
            )
        _require_number(inflow_m3_s, "inflow_m3_s")
        if inflow_m3_s < 0:
            raise ShwtpFederationError("inflow_m3_s must be >= 0")
        _require_nonempty(run_id, "run_id")
        _require_nonempty(workspace_id, "workspace_id")
        self._runtime = runtime
        self._inflow_m3_s = float(inflow_m3_s)
        self._run_id = run_id
        self._workspace_id = workspace_id
        self._active_window_id: str | None = None
        self._last_step: T106Step | None = None
        self._last_transfer: BoundaryTransfer | None = None

    # -- G4 participant surface -------------------------------------------
    @property
    def scope_path(self) -> StructuralPath:
        return SHWTP_T106_SCOPE_PATH

    @property
    def current_time_s(self) -> float:
        return self._runtime.state.time_s

    # -- federation seam --------------------------------------------------
    def prepare_window(self, window_id: str) -> None:
        """Provide the active window context before the coordinator runs it."""
        _validate_window_id(window_id)
        self._active_window_id = window_id

    def advance_to(self, target_time_s: float) -> tuple[BoundaryTransfer, ...]:
        """Advance T106 exactly one communication step and stage the F01 flow."""
        if self._active_window_id is None:
            raise ShwtpFederationError(
                "T106 participant has no active window prepared "
                "(stale/missing window context)"
            )
        current = self.current_time_s
        dt = self._runtime.config.dt_s
        _exact_boundary_check(current, target_time_s, dt, "T106")

        step = self._runtime.step(self._inflow_m3_s)
        self._last_step = step

        transfer = BoundaryTransfer(
            transfer_id=f"{SHWTP_FEDERATION_TRANSFER_PREFIX}-{self._active_window_id}",
            source=t106_out_port_ref(),
            target=t108_in_port_ref(),
            binding_id=SHWTP_F01_BINDING_ID,
            window_id=self._active_window_id,
            simulation_time_s=target_time_s,
            workspace_id=self._workspace_id,
            run_id=self._run_id,
            payload={SHWTP_FEDERATION_PAYLOAD_KEY: step.output_flow_m3_s},
        )
        self._last_transfer = transfer
        return (transfer,)

    def commit_transfers(self, inbound: Sequence[BoundaryTransfer]) -> None:
        """T106 is a source only; unexpected inbound transfers fail closed."""
        if inbound:
            raise ShwtpFederationError(
                "T106 participant received unexpected inbound transfer(s); "
                "T106 is a source, never a sink"
            )

    # -- inspection (tests / provenance) ----------------------------------
    @property
    def runtime(self) -> T106LogicalRuntime:
        return self._runtime

    @property
    def last_transfer(self) -> BoundaryTransfer | None:
        return self._last_transfer

    @property
    def last_step(self) -> T106Step | None:
        return self._last_step


class ShwtpT108Participant:
    """G4 participant adapter around the accepted T108 standalone runtime.

    Maintains one committed boundary-input value (the inflow available for the
    NEXT window). During ``advance_to`` it uses ONLY that committed inflow plus
    an explicit requested outflow — it never reads T106 state directly. After
    the window validates, ``commit_transfers`` validates the exact F01 transfer
    and stores its flow for the next window (no same-window retroactive step).
    """

    __slots__ = (
        "_runtime",
        "_requested_outflow_m3_s",
        "_committed_inflow_m3_s",
        "_run_id",
        "_workspace_id",
        "_active_window_id",
        "_last_step",
        "_last_committed_transfer",
    )

    def __init__(
        self,
        runtime: T108TankRuntime,
        requested_outflow_m3_s: float,
        initial_inflow_m3_s: float,
        run_id: str,
        workspace_id: str = SHWTP_WORKSPACE_ID,
    ) -> None:
        if not isinstance(runtime, T108TankRuntime):
            raise ShwtpFederationError(
                f"runtime must be T108TankRuntime, "
                f"got {type(runtime).__name__}"
            )
        _require_number(requested_outflow_m3_s, "requested_outflow_m3_s")
        _require_number(initial_inflow_m3_s, "initial_inflow_m3_s")
        if requested_outflow_m3_s < 0:
            raise ShwtpFederationError("requested_outflow_m3_s must be >= 0")
        if initial_inflow_m3_s < 0:
            raise ShwtpFederationError("initial_inflow_m3_s must be >= 0")
        _require_nonempty(run_id, "run_id")
        _require_nonempty(workspace_id, "workspace_id")
        self._runtime = runtime
        self._requested_outflow_m3_s = float(requested_outflow_m3_s)
        self._committed_inflow_m3_s = float(initial_inflow_m3_s)
        self._run_id = run_id
        self._workspace_id = workspace_id
        self._active_window_id: str | None = None
        self._last_step: T108Step | None = None
        self._last_committed_transfer: BoundaryTransfer | None = None

    # -- G4 participant surface -------------------------------------------
    @property
    def scope_path(self) -> StructuralPath:
        return SHWTP_T108_SCOPE_PATH

    @property
    def current_time_s(self) -> float:
        return self._runtime.state.time_s

    # -- federation seam --------------------------------------------------
    def prepare_window(self, window_id: str) -> None:
        """Provide the active window context before the coordinator runs it."""
        _validate_window_id(window_id)
        self._active_window_id = window_id

    def advance_to(self, target_time_s: float) -> tuple[BoundaryTransfer, ...]:
        """Advance T108 exactly one communication step using the committed
        (previous-boundary) inflow and the explicit requested outflow."""
        current = self.current_time_s
        dt = self._runtime.config.dt_s
        _exact_boundary_check(current, target_time_s, dt, "T108")

        # Uses ONLY the committed inflow; never reads T106 runtime state.
        step = self._runtime.step(
            self._committed_inflow_m3_s, self._requested_outflow_m3_s
        )
        self._last_step = step
        return ()

    def commit_transfers(self, inbound: Sequence[BoundaryTransfer]) -> None:
        """Validate the exact F01 transfer and store its flow for the NEXT
        window. No same-window retroactive re-step of T108."""
        if self._active_window_id is None:
            raise ShwtpFederationError(
                "T108 participant has no active window prepared "
                "(stale/missing window context)"
            )
        transfers = tuple(inbound)
        if len(transfers) != 1:
            raise ShwtpFederationError(
                f"T108 input expects exactly one F01 transfer per window, "
                f"got {len(transfers)}"
            )
        transfer = transfers[0]
        self._validate_f01_transfer(transfer)
        # Lag semantics: the committed value becomes available for the NEXT
        # window only; T108 already advanced with the previous committed value.
        self._committed_inflow_m3_s = float(
            transfer.payload[SHWTP_FEDERATION_PAYLOAD_KEY]
        )
        self._last_committed_transfer = transfer

    def _validate_f01_transfer(self, transfer: BoundaryTransfer) -> None:
        if not isinstance(transfer, BoundaryTransfer):
            raise ShwtpFederationError(
                f"inbound transfer must be BoundaryTransfer, "
                f"got {type(transfer).__name__}"
            )
        if transfer.source != t106_out_port_ref():
            raise ShwtpFederationError(
                f"unexpected F01 source {transfer.source.as_string()!r}; "
                f"expected {t106_out_port_ref().as_string()!r}"
            )
        if transfer.target != t108_in_port_ref():
            raise ShwtpFederationError(
                f"unexpected F01 target {transfer.target.as_string()!r}; "
                f"expected {t108_in_port_ref().as_string()!r}"
            )
        if transfer.binding_id != SHWTP_F01_BINDING_ID:
            raise ShwtpFederationError(
                f"unexpected binding {transfer.binding_id!r}; "
                f"expected {SHWTP_F01_BINDING_ID!r}"
            )
        if transfer.workspace_id != self._workspace_id:
            raise ShwtpFederationError(
                f"transfer workspace {transfer.workspace_id!r} does not match "
                f"federation workspace {self._workspace_id!r}"
            )
        if transfer.run_id != self._run_id:
            raise ShwtpFederationError(
                f"transfer run {transfer.run_id!r} does not match "
                f"federation run {self._run_id!r}"
            )
        if transfer.window_id != self._active_window_id:
            raise ShwtpFederationError(
                f"transfer window {transfer.window_id!r} does not match "
                f"active window {self._active_window_id!r}"
            )
        payload = transfer.payload
        if set(payload.keys()) != {SHWTP_FEDERATION_PAYLOAD_KEY}:
            raise ShwtpFederationError(
                f"unexpected F01 payload keys {sorted(payload.keys())!r}; "
                f"expected exactly [{SHWTP_FEDERATION_PAYLOAD_KEY!r}]"
            )
        value = payload[SHWTP_FEDERATION_PAYLOAD_KEY]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ShwtpFederationError(
                f"F01 payload {SHWTP_FEDERATION_PAYLOAD_KEY!r} must be a "
                f"finite number, got {type(value).__name__}"
            )
        if not math.isfinite(float(value)) or value < 0:
            raise ShwtpFederationError(
                f"F01 payload {SHWTP_FEDERATION_PAYLOAD_KEY!r} must be a "
                f"finite non-negative number, got {value!r}"
            )

    # -- inspection (tests / provenance) ----------------------------------
    @property
    def runtime(self) -> T108TankRuntime:
        return self._runtime

    @property
    def committed_inflow_m3_s(self) -> float:
        """The inflow value available for the NEXT window (lagged)."""
        return self._committed_inflow_m3_s

    @property
    def last_step(self) -> T108Step | None:
        return self._last_step

    @property
    def last_committed_transfer(self) -> BoundaryTransfer | None:
        return self._last_committed_transfer


class ShwtpFederation:
    """Deterministic SH-WTP T106->T108 explicit-lagged federation evaluation.

    Wraps the accepted standalone T106/T108 runtimes in the smallest G4
    participant adapters and drives them through the existing G4 ``Coordinator``
    with exactly one F01 binding. Fresh instances are isolated (no shared
    mutable state). The coupling policy is exposed — and enforced — only here.
    """

    __slots__ = (
        "_config",
        "_workspace",
        "_projection",
        "_coordinator",
        "_t106",
        "_t108",
        "_time_s",
        "_window_index",
        "_history",
    )

    def __init__(
        self,
        config: ShwtpFederationConfig,
        *,
        workspace: ShwtpWorkspace | None = None,
        projection: ShwtpF01Projection | None = None,
    ) -> None:
        if not isinstance(config, ShwtpFederationConfig):
            raise ShwtpFederationError(
                f"config must be ShwtpFederationConfig, "
                f"got {type(config).__name__}"
            )
        self._config = config

        shwtp_ws = workspace or build_shwtp_workspace()
        if not isinstance(shwtp_ws, ShwtpWorkspace):
            raise ShwtpFederationError(
                f"workspace must be ShwtpWorkspace, "
                f"got {type(shwtp_ws).__name__}"
            )
        self._workspace = shwtp_ws

        proj = projection or build_shwtp_f01_projection()
        if not isinstance(proj, ShwtpF01Projection):
            raise ShwtpFederationError(
                f"projection must be ShwtpF01Projection, "
                f"got {type(proj).__name__}"
            )
        if proj.graph.workspace_id != SHWTP_WORKSPACE_ID:
            raise ShwtpFederationError(
                f"projection graph workspace {proj.graph.workspace_id!r} "
                f"does not match {SHWTP_WORKSPACE_ID!r}"
            )
        self._projection = proj

        self._coordinator = Coordinator(self._workspace.workspace, proj.graph)

        t106_runtime = T106LogicalRuntime(
            T106Config(dt_s=config.t106_dt_s),
            RunContextV2(
                workspace_id=SHWTP_WORKSPACE_ID,
                run_id=config.run_id,
                scope_path=SHWTP_T106_SCOPE_PATH,
            ),
        )
        t108_runtime = T108TankRuntime(
            T108Config(
                capacity_m3=config.t108_capacity_m3,
                tank_area_m2=config.t108_tank_area_m2,
                initial_volume_m3=config.t108_initial_volume_m3,
                dt_s=config.t108_dt_s,
            ),
            RunContextV2(
                workspace_id=SHWTP_WORKSPACE_ID,
                run_id=config.run_id,
                scope_path=SHWTP_T108_SCOPE_PATH,
            ),
        )

        self._t106 = ShwtpT106Participant(
            t106_runtime, config.t106_inflow_m3_s, config.run_id
        )
        self._t108 = ShwtpT108Participant(
            t108_runtime,
            config.t108_requested_outflow_m3_s,
            config.initial_t108_inflow_m3_s,
            config.run_id,
        )

        self._coordinator.register(self._t106)
        self._coordinator.register(self._t108)

        self._time_s = 0.0
        self._window_index = 0
        self._history: list[WindowOutcome] = []

    # -- identity / policy -------------------------------------------------
    @property
    def coupling_policy(self) -> str:
        """The single authorized orchestration policy (explicit_lagged)."""
        return SHWTP_FEDERATION_COUPLING_POLICY

    @property
    def config(self) -> ShwtpFederationConfig:
        return self._config

    @property
    def workspace_id(self) -> str:
        return SHWTP_WORKSPACE_ID

    @property
    def participants(self) -> tuple[str, ...]:
        return ("shwtp/line1/l1_t106", "shwtp/line1/l1_t108")

    @property
    def binding_id(self) -> str:
        return SHWTP_F01_BINDING_ID

    @property
    def time_s(self) -> float:
        return self._time_s

    @property
    def window_index(self) -> int:
        return self._window_index

    @property
    def coordinator(self) -> Coordinator:
        return self._coordinator

    @property
    def t106(self) -> ShwtpT106Participant:
        return self._t106

    @property
    def t108(self) -> ShwtpT108Participant:
        return self._t108

    @property
    def history(self) -> tuple[WindowOutcome, ...]:
        return tuple(self._history)

    # -- execution ---------------------------------------------------------
    def run_window(self, window_id: str) -> WindowOutcome:
        """Prepare the active window context, then execute one coordination
        boundary through the existing G4 Coordinator.

        Fails closed on a stale/wrong/future window id or a non-exact boundary.
        """
        _validate_window_id(window_id)
        expected_index = self._window_index + 1
        if window_id != f"{SHWTP_FEDERATION_WINDOW_PREFIX}{expected_index}":
            raise ShwtpFederationError(
                f"stale/wrong window {window_id!r}; expected "
                f"{SHWTP_FEDERATION_WINDOW_PREFIX}{expected_index!r}"
            )
        target_time_s = self._time_s + self._config.communication_step_s

        # Smallest SH-WTP federation seam: prepare the active window context
        # on the participant adapters BEFORE the coordinator runs the window.
        self._t106.prepare_window(window_id)
        self._t108.prepare_window(window_id)

        outcome = self._coordinator.run_window(window_id, target_time_s)
        self._history.append(outcome)
        if outcome.status == "completed":
            self._time_s = target_time_s
            self._window_index = expected_index
        return outcome

    def serialize(self) -> dict:
        """Deterministic machine-readable federation inspection."""
        t106_state = self._t106.runtime.state
        t108_state = self._t108.runtime.state
        return {
            "schema": "vf.vnext.g14b.shwtp.federation.v1",
            "coupling_policy": self.coupling_policy,
            "workspace_id": self.workspace_id,
            "run_id": self._config.run_id,
            "communication_step_s": self._config.communication_step_s,
            "participants": list(self.participants),
            "binding_id": self.binding_id,
            "time_s": self._time_s,
            "window_index": self._window_index,
            "t108_committed_inflow_m3_s": self._t108.committed_inflow_m3_s,
            "t106_state": {
                "time_s": t106_state.time_s,
                "last_input_flow_m3_s": t106_state.last_input_flow_m3_s,
                "last_output_flow_m3_s": t106_state.last_output_flow_m3_s,
            },
            "t108_state": {
                "time_s": t108_state.time_s,
                "volume_m3": t108_state.volume_m3,
                "level_m": t108_state.level_m,
            },
            "history": [
                {
                    "window_id": o.window_id,
                    "target_time_s": o.target_time_s,
                    "participants": list(o.participants),
                    "committed": list(o.committed),
                    "status": o.status,
                    "failure": o.failure,
                }
                for o in self._history
            ],
        }
