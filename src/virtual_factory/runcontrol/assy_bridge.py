"""G7-C — ASSY execution bridge (TipaAssyFederation + AssySubLineAdapter + G4).

Reuses the accepted G5 federation + G4 Coordinator seams to advance ASSY
sub-lines at LEGITIMATE natural coordination boundaries only. No AssyLineRuntime
rewrite, no demo-policy promotion, no new synchronization rule, no fractional
dwell/index.

A "step" for a set of ASSY sub-lines advances to the next natural common
boundary (current time + nominal dwell). If a selected sub-line cannot reach the
target exactly through its natural dwell/index cadence, the G4 coordinator fails
closed (the lifecycle service then marks the run failed).

VF-vNEXT-R1 — ASSY-domain hold/freeze seam (smallest necessary capability):
a held sub-line is simply NOT registered for the coordination window, so its
runtime is never touched while the remaining sub-lines advance independently.
This is a domain-scoped bridge capability (used by evidence/tests); it adds no
generic Workspace lifecycle or coordinator/synchronization policy.
"""

from __future__ import annotations

from virtual_factory.federation import TipaAssyFederation
from virtual_factory.runcontrol.lifecycle import StepResult


class AssyExecutionBridge:
    """Execution bridge over one ``TipaAssyFederation``."""

    def __init__(self, federation: TipaAssyFederation) -> None:
        if not isinstance(federation, TipaAssyFederation):
            raise TypeError(
                f"federation must be TipaAssyFederation, got {type(federation).__name__}"
            )
        self._federation = federation
        self._window_seq = 0
        self._held_sub_line_ids: set[str] = set()

    @property
    def federation(self) -> TipaAssyFederation:
        """The federation this bridge executes (domain truth owner)."""
        return self._federation

    # ── R1: ASSY-domain hold/freeze seam ─────────────────────

    @property
    def held_sub_line_ids(self) -> tuple[str, ...]:
        """Deterministic sorted sub-line ids currently held/frozen."""
        return tuple(sorted(self._held_sub_line_ids))

    def hold_sub_line(self, sub_line_id: str) -> None:
        """Hold (freeze) ONE canonical sub-line (unknown id fails closed)."""
        self._federation.get(sub_line_id)  # fail closed on unknown id
        self._held_sub_line_ids.add(sub_line_id)

    def release_sub_line(self, sub_line_id: str) -> None:
        """Release a previously held sub-line (unknown id fails closed)."""
        self._federation.get(sub_line_id)
        self._held_sub_line_ids.discard(sub_line_id)

    def _executable_ids(self, scope_ids: tuple[str, ...]) -> tuple[str, ...]:
        """Selected ids that may actually participate (held lines excluded)."""
        return tuple(sid for sid in tuple(scope_ids) if sid not in self._held_sub_line_ids)

    @property
    def supports_reset(self) -> bool:
        # AssyLineRuntime exposes an accepted public in-context reset().
        return True

    def sub_line_views(self) -> tuple[dict, ...]:
        """READ-ONLY per-sub-line monitor projection (G24-C01).

        Returns one detached dict per TIPA ASSY sub-line, reading only the
        public runtime read surface (simulation time, conveyor state, WIP and
        motor counts, RSO2 buffer). Never mutates the federation, a runtime or
        a sub-line; the domain runtime remains the truth owner.
        """
        rows: list[dict] = []
        for sub_line_id in self._federation.sub_line_ids:
            sub = self._federation.get(sub_line_id)
            runtime = sub.runtime
            identity = sub.identity
            rows.append({
                "sub_line_id": sub_line_id,
                "scope": sub.path.as_string(),
                "variant": (identity.variant if identity is not None else ""),
                "simulation_time_s": runtime.simulation_time_s,
                "conveyor_state": runtime.conveyor.state.value,
                "wip_count": runtime.wip_count,
                "motor_count": runtime.motor_count,
                "rso2_buffer_size": runtime.rso2_buffer_size,
            })
        return tuple(rows)

    def natural_next_boundary(self, scope_ids: tuple[str, ...]) -> float:
        ids = self._executable_ids(scope_ids)
        if not ids:
            raise ValueError("no executable sub-lines to advance")
        nominal = (
            self._federation.get(ids[0]).config.conveyor.nominal_line_dwell_time_s
        )
        current = max(
            self._federation.get(sid).runtime.simulation_time_s for sid in ids
        )
        return current + nominal

    def advance(
        self,
        target_time_s: float,
        scope_ids: tuple[str, ...],
        window_id: str,
    ) -> StepResult:
        ids = self._executable_ids(scope_ids)
        if not ids:
            # Every selected sub-line is held/frozen: no executable participant,
            # so nothing may advance (fail closed, never fabricate a success).
            return StepResult(
                status="failed",
                target_time_s=target_time_s,
                participants=(),
                committed=(),
                failure=(
                    "all selected ASSY sub-lines are held/frozen; no executable "
                    "participant is available"
                ),
            )
        self._window_seq += 1
        coordinator = self._federation.make_coordinator()
        outcome = self._federation.run_window(
            coordinator,
            target_time_s,
            sub_line_ids=ids,
            window_id=window_id,
        )
        return StepResult(
            status=outcome.status,
            target_time_s=outcome.target_time_s,
            participants=outcome.participants,
            committed=outcome.committed,
            failure=outcome.failure,
        )

    def reset(self, scope_ids: tuple[str, ...]) -> None:
        # Capability-scoped in-context reset via the existing public runtime
        # contract (same object, time back to 0). Never rebuilds run identity.
        # R1: a prepared sub-line is re-prepared from its immutable run profile
        # so the reset state is profile-consistent (same as a fresh run).
        #
        # R1-C01: the ASSY-domain HOLD/FREEZE state of the reset scopes is
        # cleared as part of the reset, so a canonical session reset returns the
        # whole session to its fresh profile baseline with every sub-line able to
        # participate and progress again. It is capability-scoped on purpose: a
        # full session reset (all six effective scopes) clears every domain hold.
        self._held_sub_line_ids.difference_update(scope_ids)
        for sid in tuple(scope_ids):
            self._federation.reset_sub_line(sid)
