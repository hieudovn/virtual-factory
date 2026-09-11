"""ASSY sub-line runtime participant adapter (G5-B).

Wraps an EXISTING :class:`AssyLineRuntime` instance so it can participate in
the G4 executable-participant seam WITHOUT modifying ``AssyLineRuntime``
internals.

Contract (Issue #50 section B):
- the adapter owns a fixed G1 sub-line :class:`StructuralPath`;
- ``current_time_s`` delegates to the wrapped runtime's ``simulation_time_s``;
- advancement uses ONLY existing public ASSY runtime operations, executed in
  the same order as the ASSY regression-oracle driver
  (``execute_dwell()`` then ``index_line()`` when ``READY_TO_INDEX``);
- no duplicate WIP/conveyor/quality/genealogy truth — all domain state stays in
  the wrapped runtime;
- no one-engine-per-scope abstraction beyond the wrapped runtime;
- no direct cross-scope state access; ``commit_transfers`` rejects any inbound
  boundary exchange (ASSY sub-lines exchange nothing at G5 boundaries).

VF-vNEXT-R1 — prepared-production mode (additive, opt-in):
when the adapter is given the sub-line's shared run state + immutable run
profile, ``natural_step`` executes the ACCEPTED six-sub-line production driver
(feed replenishment -> on-demand RSO2 for AP04 -> ``execute_dwell()`` ->
``index_line()`` when ``READY_TO_INDEX`` -> introduce the next SSO2 through the
existing public entry) via the shared :func:`step_prepared_line` helper.
Without run state the adapter keeps the frozen structural step above, so the G5
standalone/federated parity semantics are unchanged. The adapter still owns no
truth: positions, WIP, quality and genealogy stay in the wrapped runtime.

Boundary rule (Issue #50): the adapter NEVER invents fractional dwell/index or
rewrites ASSY time semantics to satisfy an arbitrary coordinator target. It
reports success only when the natural advancement of the wrapped runtime lands
EXACTLY on the requested target; otherwise it fails closed with
:class:`ParticipantError` (the boundary is not legitimately reachable without a
new synchronization/time policy, which is out of G5 scope).
"""

from __future__ import annotations

from typing import Sequence

from virtual_factory.assembly import (
    AssyLineRuntime,
    ConveyorState,
)
from virtual_factory.assembly.assy_run_profile import (
    AssyRunProfile,
    AssySubLineRunState,
    step_prepared_line,
)
from virtual_factory.composition import (
    BoundaryTransfer,
    ParticipantError,
)
from virtual_factory.composition.participant import ExecutableParticipant
from virtual_factory.workspace import StructuralPath


class AssySubLineAdapter:
    """G4 :class:`ExecutableParticipant` adapter over one AssyLineRuntime.

    Structurally conforms to the G4 participant protocol (duck-typed; verified
    by ``Coordinator.register`` and by the runtime-checkable protocol).
    """

    def __init__(
        self,
        scope_path: StructuralPath,
        runtime: AssyLineRuntime,
        *,
        run_state: AssySubLineRunState | None = None,
        run_profile: AssyRunProfile | None = None,
    ) -> None:
        if not isinstance(scope_path, StructuralPath):
            raise TypeError(
                "scope_path must be a G1 StructuralPath, "
                f"got {type(scope_path).__name__}"
            )
        if scope_path.is_workspace_root:
            raise ParticipantError(
                "an ASSY sub-line adapter requires a scope path, "
                "not the workspace root"
            )
        if not isinstance(runtime, AssyLineRuntime):
            raise TypeError(
                "runtime must be an existing AssyLineRuntime, "
                f"got {type(runtime).__name__}"
            )
        if run_state is not None and run_profile is None:
            raise TypeError(
                "a run state requires the immutable run profile that owns its "
                "feed/sequencing inputs"
            )
        self._scope_path = scope_path
        self._runtime = runtime
        self._run_state = run_state
        self._run_profile = run_profile

    # ── prepared-production state (R1) ────────────────────────

    @property
    def run_state(self) -> AssySubLineRunState | None:
        """The per-sub-line run state (feed/sequencing) or ``None``."""
        return self._run_state

    @property
    def run_profile(self) -> AssyRunProfile | None:
        """The immutable run profile pinning this sub-line's run inputs."""
        return self._run_profile

    @property
    def is_prepared(self) -> bool:
        """Whether this adapter drives accepted production semantics."""
        return self._run_state is not None and self._run_profile is not None

    # ── G4 participant protocol ──────────────────────────────

    @property
    def scope_path(self) -> StructuralPath:
        """The fixed G1 structural scope the wrapped runtime is bound to."""
        return self._scope_path

    @property
    def current_time_s(self) -> float:
        """Delegate to the wrapped ASSY runtime's simulation time."""
        return self._runtime.simulation_time_s

    def advance_to(self, target_time_s: float) -> tuple[BoundaryTransfer, ...]:
        """Advance the wrapped runtime to an EXACTLY reachable boundary.

        Uses only existing public ASSY runtime operations (dwell + conditional
        index). Fails closed (never fabricates time) if a natural advancement
        overshoots the requested target.
        """
        if target_time_s < self._runtime.simulation_time_s:
            raise ParticipantError(
                "cannot move ASSY simulation time backward from "
                f"{self._runtime.simulation_time_s!r} to {target_time_s!r}"
            )
        while self._runtime.simulation_time_s < target_time_s:
            self.natural_step()
            if self._runtime.simulation_time_s > target_time_s:
                raise ParticipantError(
                    "natural ASSY boundary "
                    f"{self._runtime.simulation_time_s!r} overshoots requested "
                    f"target {target_time_s!r}; this boundary is not reachable "
                    "without fractional dwell/time rewrite"
                )
        if self._runtime.simulation_time_s != target_time_s:
            raise ParticipantError(
                "ASSY runtime did not land exactly on target "
                f"{target_time_s!r}: reported {self._runtime.simulation_time_s!r}"
            )
        return ()

    def commit_transfers(
        self, inbound: Sequence[BoundaryTransfer]
    ) -> None:
        """ASSY sub-lines exchange nothing at G5 boundaries (fail closed)."""
        if inbound:
            raise ParticipantError(
                "ASSY sub-line adapter accepts no inbound boundary transfers (G5)"
            )

    # ── ASSY-specific helpers ─────────────────────────────────

    @property
    def runtime(self) -> AssyLineRuntime:
        """The wrapped runtime — the single source of ASSY domain truth."""
        return self._runtime

    def natural_step(self) -> None:
        """Execute one natural ASSY advancement step (public ops only).

        Unprepared (frozen G5 structural) mode mirrors the ASSY regression-oracle
        driver: one dwell, then one index when the line is ready.

        Prepared (R1) mode executes the accepted production driver through the
        shared helper: optional bounded feed replenishment, on-demand RSO2 for
        AP04, one dwell, one index when ready, then the next SSO2 introduction.
        """
        if self._run_state is None or self._run_profile is None:
            self._runtime.execute_dwell()
            if self._runtime.conveyor.state == ConveyorState.READY_TO_INDEX:
                self._runtime.index_line()
            return
        step_prepared_line(
            self._runtime,
            self._run_state,
            feed_policy=(
                self._run_profile.feed_policy
                if self._run_profile.continuous_feed_enabled
                else None
            ),
        )


# Re-export for runtime-checkable protocol conformance assertions in tests.
__all__ = ["AssySubLineAdapter", "ExecutableParticipant"]
